"""Routes de gestion des documents (PRD-02).

- POST /api/documents — upload (multipart) avec déduplication SHA-256
- GET /api/documents — recherche/liste paginée
- GET /api/documents/{id} — métadonnées
- PUT /api/documents/{id} — modification métadonnées
- DELETE /api/documents/{id} — soft delete (superviseur)
- GET /api/documents/{id}/contenu — streaming déchiffré (visionneuse)
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError

from app.api.deps import (
    AgentArchivisteOuPlus,
    AgentCourant,
    AgentSuperviseur,
    IpClient,
    SessionDB,
)
from app.config import get_settings
from app.models import Document, DocumentSousDossier
from app.schemas.document import (
    DocumentLecture,
    DocumentMetadonnees,
    DocumentMiseAJour,
    EmplacementResume,
    NiveauResume,
)
from app.services.audit import journaliser
from app.services.storage import stocker, stream_dechiffre
from app.tasks.extraction_doc import (
    STATUT_OCR_EN_ATTENTE,
    extraire_et_indexer,
)

router = APIRouter(prefix="/documents", tags=["documents"])


async def _emplacements_pour(
    db, document_ids: list[int], tenant_id: int
) -> dict[int, EmplacementResume]:
    """Renvoie un mapping {document_id: EmplacementResume} pour les ids fournis.

    Un seul SQL — JOIN sur les 6 niveaux + filtre tenant via sites.tenant_id.
    Renvoie un dict vide si la liste est vide.
    """
    if not document_ids:
        return {}
    sql = text(
        """
        SELECT
            dsd.document_id,
            sd.id AS sous_dossier_id,
            lpad(s.numero::text, 2, '0')
              || '.' || lpad(l.numero::text, 2, '0')
              || '.' || lpad(r.numero::text, 2, '0')
              || '.' || lpad(b.numero::text, 3, '0')
              || '.' || lpad(d.numero::text, 2, '0')
              || '.' || lpad(sd.numero::text, 2, '0') AS code_complet,
            s.numero AS site_num, s.libelle AS site_lib,
            l.numero AS local_num, l.libelle AS local_lib,
            r.numero AS rayon_num, r.libelle AS rayon_lib,
            b.numero AS boite_num, b.libelle AS boite_lib,
            d.numero AS dossier_num, d.libelle AS dossier_lib,
            sd.numero AS sd_num, sd.libelle AS sd_lib
        FROM documents_sous_dossiers dsd
        JOIN sous_dossiers sd ON sd.id = dsd.sous_dossier_id
        JOIN dossiers_classeurs d ON d.id = sd.dossier_id
        JOIN boites b              ON b.id = d.boite_id
        JOIN rayons r              ON r.id = b.rayon_id
        JOIN locaux_salles l       ON l.id = r.local_id
        JOIN sites s               ON s.id = l.site_id
        WHERE dsd.document_id = ANY(:doc_ids) AND s.tenant_id = :tenant_id
        """
    )
    rows = (
        await db.execute(sql, {"doc_ids": document_ids, "tenant_id": tenant_id})
    ).mappings().all()
    return {
        r["document_id"]: EmplacementResume(
            sous_dossier_id=r["sous_dossier_id"],
            code_complet=r["code_complet"],
            site=NiveauResume(numero=r["site_num"], libelle=r["site_lib"]),
            local=NiveauResume(numero=r["local_num"], libelle=r["local_lib"]),
            rayon=NiveauResume(numero=r["rayon_num"], libelle=r["rayon_lib"]),
            boite=NiveauResume(numero=r["boite_num"], libelle=r["boite_lib"]),
            dossier=NiveauResume(numero=r["dossier_num"], libelle=r["dossier_lib"]),
            sous_dossier=NiveauResume(numero=r["sd_num"], libelle=r["sd_lib"]),
        )
        for r in rows
    }


def _enrichir(doc: Document, emp: EmplacementResume | None) -> DocumentLecture:
    """Construit un DocumentLecture en injectant l'emplacement."""
    return DocumentLecture.model_validate(doc).model_copy(update={"emplacement": emp})


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=DocumentLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Uploader un document",
)
async def uploader(
    request: Request,
    db: SessionDB,
    agent: AgentArchivisteOuPlus,
    ip: IpClient,
    background_tasks: BackgroundTasks,
    fichier: Annotated[UploadFile, File(description="Fichier binaire à uploader")],
    metadonnees: Annotated[
        str,
        Form(
            description=(
                "JSON sérialisé des métadonnées (titre, categorie_id obligatoire, "
                "description, resume, mots_cles, thematique_id, type_document_id, "
                "date_document, confidentiel, sous_dossier_id)."
            ),
        ),
    ],
) -> Document:
    # 1. Parser et valider les métadonnées
    try:
        meta = DocumentMetadonnees.model_validate(json.loads(metadonnees))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Métadonnées invalides : {exc}",
        ) from exc

    # 2. Vérifier la taille avant lecture complète
    settings = get_settings()
    taille_max = settings.max_upload_size_mb * 1024 * 1024
    contenu = await fichier.read()
    if len(contenu) > taille_max:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.max_upload_size_mb} Mo)",
        )

    # 3. Chiffrement + stockage + checksum + détection MIME
    stocke = await stocker(contenu, tenant_id=agent.tenant_id)

    # 4. Déduplication par checksum
    existant = await db.execute(
        select(Document).where(
            Document.tenant_id == agent.tenant_id,
            Document.checksum_sha256 == stocke.checksum_sha256,
            Document.supprime.is_(False),
        )
    )
    doc_existant = existant.scalar_one_or_none()
    if doc_existant is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Ce fichier est déjà présent (document #{doc_existant.id}, "
                f"« {doc_existant.titre} »)."
            ),
            headers={"X-Document-Existant-Id": str(doc_existant.id)},
        )

    # 5. Création de l'enregistrement
    document = Document(
        tenant_id=agent.tenant_id,
        titre=meta.titre,
        description=meta.description,
        resume=meta.resume,
        mots_cles=meta.mots_cles,
        categorie_id=meta.categorie_id,
        thematique_id=meta.thematique_id,
        type_document_id=meta.type_document_id,
        mime=stocke.mime,
        taille_octets=stocke.taille_octets,
        checksum_sha256=stocke.checksum_sha256,
        chemin_stockage=stocke.chemin_relatif,
        nonce=stocke.nonce,
        date_document=meta.date_document,
        date_numerisation=datetime.now(timezone.utc),
        confidentiel=meta.confidentiel,
        origine="upload",
        # Le statut est mis à "ocr_en_attente" — la background task qui
        # extrait le texte le passera à "pret" ou "ocr_echoue".
        statut=STATUT_OCR_EN_ATTENTE,
        created_by=agent.id,
    )
    db.add(document)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Référence invalide (catégorie/thématique/type) : {exc.orig}",
        ) from exc

    # 6. Lien optionnel vers sous-dossier physique
    if meta.sous_dossier_id is not None:
        db.add(
            DocumentSousDossier(
                document_id=document.id,
                sous_dossier_id=meta.sous_dossier_id,
            )
        )

    # 7. Audit
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="document.upload",
        entite="documents",
        entite_id=document.id,
        payload={
            "titre": document.titre,
            "mime": document.mime,
            "taille_octets": document.taille_octets,
        },
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(document)

    # Lance l'extraction de texte en arrière-plan. La tâche ouvre sa propre
    # session DB — elle ne dépend pas de celle de la requête.
    background_tasks.add_task(extraire_et_indexer, document.id, agent.tenant_id)

    return document


# ---------------------------------------------------------------------------
# Liste / recherche
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[DocumentLecture],
    summary="Lister les documents du tenant (filtrable)",
)
async def lister(
    agent: AgentCourant,
    db: SessionDB,
    q: str | None = Query(None, description="Recherche plein texte"),
    categorie_id: int | None = Query(None),
    statut: str | None = Query(None),
    incomplete: bool = Query(
        False,
        description="Si true, ne retourne que les documents avec thématique OU type de document manquant",
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[Document]:
    base = select(Document).where(
        Document.tenant_id == agent.tenant_id,
        Document.supprime.is_(False),
    )

    if statut:
        base = base.where(Document.statut == statut)
    if categorie_id is not None:
        base = base.where(Document.categorie_id == categorie_id)
    if incomplete:
        # Métadonnées incomplètes = au moins une dimension de classement
        # secondaire manquante. La catégorie est obligatoire à la création
        # donc on ne la teste pas ici ; on cible les imports en masse.
        base = base.where(
            or_(
                Document.thematique_id.is_(None),
                Document.type_document_id.is_(None),
            )
        )
    if q:
        # Recherche FTS sur recherche_fts (déjà tsvector french_unaccent)
        tsquery = func.to_tsquery("french_unaccent", _normaliser_pour_tsquery(q))
        base = base.where(tsquery.op("@@")(Document.recherche_fts))
        # Tri par pertinence — ts_rank pondère selon les poids du tsvector
        # (A=titre, B=mots_cles/résumé, C=contenu OCR).
        base = base.order_by(
            func.ts_rank(Document.recherche_fts, tsquery).desc(),
            Document.created_at.desc(),
        )
    else:
        base = base.order_by(Document.created_at.desc())
    base = base.limit(limit).offset(offset)
    result = await db.execute(base)
    documents = list(result.scalars())
    emplacements = await _emplacements_pour(
        db, [d.id for d in documents], agent.tenant_id
    )
    return [_enrichir(d, emplacements.get(d.id)) for d in documents]


def _normaliser_pour_tsquery(q: str) -> str:
    """Convertit une recherche libre en expression `tsquery` `mot1 & mot2`."""
    tokens = [t for t in q.split() if t.strip()]
    if not tokens:
        return "''"
    # Échapper les ' et combiner avec &
    safe = [t.replace("'", "''") + ":*" for t in tokens]
    return " & ".join(safe)


# ---------------------------------------------------------------------------
# Détail / MAJ / suppression
# ---------------------------------------------------------------------------


@router.get(
    "/{document_id}",
    response_model=DocumentLecture,
    summary="Métadonnées d'un document",
)
async def lire(
    document_id: int, agent: AgentCourant, db: SessionDB
) -> DocumentLecture:
    doc = await _charger(db, document_id, agent.tenant_id)
    if doc.confidentiel and agent.role.code == "agent_standard":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document confidentiel — accès restreint",
        )
    emplacements = await _emplacements_pour(db, [doc.id], agent.tenant_id)
    return _enrichir(doc, emplacements.get(doc.id))


@router.put(
    "/{document_id}",
    response_model=DocumentLecture,
    summary="Modifier les métadonnées d'un document (archiviste, superviseur ou auteur)",
)
async def maj(
    document_id: int,
    body: DocumentMiseAJour,
    request: Request,
    db: SessionDB,
    agent: AgentCourant,
    ip: IpClient,
) -> DocumentLecture:
    doc = await _charger(db, document_id, agent.tenant_id)

    # Droits : archiviste / superviseur / créateur
    if agent.role.code == "agent_standard" and doc.created_by != agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas autorisé à modifier ce document",
        )

    # Seul superviseur peut modifier `confidentiel`
    if body.confidentiel is not None and agent.role.code != "superviseur":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un superviseur peut modifier le statut confidentiel",
        )

    diff: dict[str, object] = {}
    for champ in (
        "titre",
        "description",
        "resume",
        "mots_cles",
        "categorie_id",
        "thematique_id",
        "type_document_id",
        "date_document",
        "confidentiel",
    ):
        nouvelle = getattr(body, champ)
        if nouvelle is not None and nouvelle != getattr(doc, champ):
            # JSONB ne sait pas sérialiser nativement date/datetime — on convertit
            # en chaîne ISO 8601. Sans ça, l'INSERT dans audit_log plante avec
            # `Object of type date is not JSON serializable`.
            diff[champ] = (
                nouvelle.isoformat() if isinstance(nouvelle, (date, datetime)) else nouvelle
            )
            setattr(doc, champ, nouvelle)

    # Emplacement physique (relation N:N) : on n'agit que si le champ est
    # explicitement présent dans le JSON. `null` = retirer le lien, valeur
    # entière = remplacer le lien existant.
    if "sous_dossier_id" in body.model_fields_set:
        await db.execute(
            delete(DocumentSousDossier).where(
                DocumentSousDossier.document_id == doc.id
            )
        )
        if body.sous_dossier_id is not None:
            db.add(
                DocumentSousDossier(
                    document_id=doc.id,
                    sous_dossier_id=body.sous_dossier_id,
                )
            )
        diff["sous_dossier_id"] = body.sous_dossier_id

    if not diff:
        emplacements = await _emplacements_pour(db, [doc.id], agent.tenant_id)
        return _enrichir(doc, emplacements.get(doc.id))

    doc.updated_by = agent.id
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="document.update",
        entite="documents",
        entite_id=doc.id,
        payload={"diff": diff},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(doc)
    # Recharge l'emplacement frais pour que la réponse soit complète et
    # que le frontend n'ait pas besoin d'un round-trip supplémentaire.
    emplacements = await _emplacements_pour(db, [doc.id], agent.tenant_id)
    return _enrichir(doc, emplacements.get(doc.id))


@router.post(
    "/{document_id}/reextraire",
    response_model=DocumentLecture,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Relancer l'extraction de texte (archiviste ou superviseur)",
)
async def reextraire(
    document_id: int,
    archiviste: AgentArchivisteOuPlus,
    db: SessionDB,
    background_tasks: BackgroundTasks,
    request: Request,
    ip: IpClient,
) -> DocumentLecture:
    """Relance l'extraction de texte d'un document existant.

    Utile après une mise à jour de la stratégie d'OCR (changement de pack
    de langue, passage de Tesseract à un autre provider, etc.) ou pour
    récupérer les documents marqués `ocr_echoue` après un fix
    d'environnement (Tesseract réinstallé, par exemple).
    """
    doc = await _charger(db, document_id, archiviste.tenant_id)

    # Marqué "en attente" pour que l'UI montre immédiatement que ça bouge
    doc.statut = STATUT_OCR_EN_ATTENTE
    await journaliser(
        db,
        tenant_id=archiviste.tenant_id,
        agent_id=archiviste.id,
        action="document.reextraire",
        entite="documents",
        entite_id=doc.id,
        payload={"statut_avant": doc.statut},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(extraire_et_indexer, doc.id, archiviste.tenant_id)

    emplacements = await _emplacements_pour(db, [doc.id], archiviste.tenant_id)
    return _enrichir(doc, emplacements.get(doc.id))


@router.delete(
    "/{document_id}",
    response_model=DocumentLecture,
    summary="Soft delete d'un document (superviseur)",
)
async def supprimer(
    document_id: int,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Document:
    doc = await _charger(db, document_id, superviseur.tenant_id)

    # Vérifier l'absence de liens actifs
    nb_liens = await db.scalar(
        select(func.count(DocumentSousDossier.document_id)).where(
            DocumentSousDossier.document_id == doc.id
        )
    )
    if nb_liens and nb_liens > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Ce document est lié à {nb_liens} sous-dossier(s) physique(s). "
                "Supprime ces liens avant de supprimer le document."
            ),
        )

    if doc.supprime:
        return doc  # idempotent

    doc.supprime = True
    doc.updated_by = superviseur.id
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="document.supprimer",
        entite="documents",
        entite_id=doc.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Streaming du contenu déchiffré
# ---------------------------------------------------------------------------


@router.get(
    "/{document_id}/contenu",
    summary="Récupérer le contenu déchiffré (streaming)",
)
async def contenu(
    document_id: int,
    agent: AgentCourant,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> StreamingResponse:
    doc = await _charger(db, document_id, agent.tenant_id)

    if doc.statut == "quarantaine":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document en quarantaine — contenu non accessible",
        )
    if doc.confidentiel and agent.role.code == "agent_standard":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document confidentiel — accès restreint",
        )

    # Audit (un par appel — le déduplication via cache Redis viendra avec PRD-03)
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="document.consulter",
        entite="documents",
        entite_id=doc.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    # Disposition selon le type
    disposition = "inline" if doc.mime.startswith(("application/pdf", "image/")) else "attachment"
    nom_fichier = doc.titre.replace('"', "").replace("/", "_")[:200]

    return StreamingResponse(
        stream_dechiffre(doc.chemin_stockage, tenant_id=agent.tenant_id),
        media_type=doc.mime,
        headers={
            "Content-Disposition": f'{disposition}; filename="{nom_fichier}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------


async def _charger(db, document_id: int, tenant_id: int) -> Document:
    """Charge un document non supprimé du tenant courant. HTTP 404 sinon."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
            Document.supprime.is_(False),
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable"
        )
    return doc
