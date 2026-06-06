"""Routes du module GEC (PRD-06A).

Routes couvertes dans ce fichier :
- GET /api/courriers/corbeilles/compteurs : compteurs des 8 corbeilles
- GET /api/courriers : liste filtrable par corbeille
- GET /api/courriers/{id} : détail (avec copies, notes, historique)
- POST /api/courriers : créer un courrier (multipart : pièce principale + JSON)
- POST /api/courriers/{id}/copies : mettre en copie
- POST /api/courriers/{id}/imputer : transférer la propriété
- POST /api/courriers/{id}/repondre : créer un courrier sortant lié
- POST /api/courriers/{id}/envoyer : clôturer (statut → traite)
- POST /api/courriers/{id}/notes : ajouter une note
- POST /api/courriers/{id}/documents : ajouter une pièce additionnelle
- DELETE /api/courriers/{id} : soft delete (superviseur)
"""

from __future__ import annotations

import json
from datetime import date as date_type
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    AgentCourant,
    AgentSuperviseur,
    IpClient,
    SessionDB,
)
from app.models import (
    ActionCourrier,
    Agent,
    CopieCourrier,
    Correspondant,
    Courrier,
    Document,
    DocumentCourrier,
    HistoriqueCourrier,
    Imputation,
    NoteCourrier,
    StatutCourrier,
)
from app.schemas.courrier import (
    AgentResume,
    CompteurCorbeille,
    CompteursCorbeilles,
    CopieBody,
    CorrespondantResume,
    CourrierCreation,
    CourrierDetail,
    CourrierLecture,
    HistoriqueLecture,
    ImputerBody,
    NoteCreation,
    NoteLecture,
    RepondreBody,
)
from app.services.audit import journaliser
from app.services.notifications import notifier_nouveau_courrier
from app.services.numerotation_courrier import prochain_numero_enregistrement
from app.services.storage import stocker

from app.config import get_settings

router = APIRouter(prefix="/courriers", tags=["courriers"])


# ============================================================================
# Helpers communs
# ============================================================================


# Codes des statuts seedés en 06A (cf. migration 005)
STATUT_A_TRAITER = 1
STATUT_TRAITE = 2

# Codes des actions seedées en 06A (cf. migration 005)
ACTION_CREATION = 1
ACTION_COPIE = 2
ACTION_IMPUTATION = 3
ACTION_REPONSE = 4
ACTION_ENVOI = 5
ACTION_NOTE = 6
ACTION_AJOUT_DOCUMENT = 7


async def _charger_courrier(
    db: AsyncSession, courrier_id: int, tenant_id: int
) -> Courrier:
    """Charge un courrier en vérifiant le tenant + filtrage soft delete."""
    result = await db.execute(
        select(Courrier).where(
            Courrier.id == courrier_id,
            Courrier.tenant_id == tenant_id,
            Courrier.supprime.is_(False),
        )
    )
    courrier = result.scalar_one_or_none()
    if courrier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Courrier introuvable"
        )
    return courrier


async def _agent_voit_courrier(
    db: AsyncSession, courrier: Courrier, agent_id: int
) -> bool:
    """Détermine si un agent voit un courrier (propriétaire OU en copie OU créateur)."""
    if courrier.agent_proprietaire_id == agent_id:
        return True
    if courrier.created_by == agent_id:
        return True
    nb = await db.scalar(
        select(func.count(CopieCourrier.agent_id)).where(
            CopieCourrier.courrier_id == courrier.id,
            CopieCourrier.agent_id == agent_id,
        )
    )
    return bool(nb)


async def _ajouter_historique(
    db: AsyncSession,
    courrier_id: int,
    agent_id: int,
    action_id: int,
    payload: dict | None = None,
) -> None:
    """Ajoute une ligne dans historiques_courrier sans commit."""
    db.add(
        HistoriqueCourrier(
            courrier_id=courrier_id,
            agent_id=agent_id,
            action_id=action_id,
            payload=payload or {},
        )
    )


# ============================================================================
# Corbeilles — compteurs
# ============================================================================


@router.get("/corbeilles/compteurs", response_model=CompteursCorbeilles)
async def compteurs_corbeilles(
    agent: AgentCourant, db: SessionDB
) -> CompteursCorbeilles:
    """Compteurs des 8 corbeilles pour l'agent connecté.

    PRD-06A : 4 corbeilles actives (a_traiter, traite, en_copie, en_retard).
    Les 4 autres (workflow validation) sont marquées `actif_en_06a=False`
    avec un compteur figé à 0.
    """
    aujourd_hui = date_type.today()

    # A traiter : statut = a_traiter ET propriétaire = moi
    a_traiter = await db.scalar(
        select(func.count(Courrier.id)).where(
            Courrier.tenant_id == agent.tenant_id,
            Courrier.supprime.is_(False),
            Courrier.statut_id == STATUT_A_TRAITER,
            Courrier.agent_proprietaire_id == agent.id,
        )
    )

    # Traités : statut = traite ET je suis (ou j'ai été) le porteur OU le créateur
    traite = await db.scalar(
        select(func.count(Courrier.id)).where(
            Courrier.tenant_id == agent.tenant_id,
            Courrier.supprime.is_(False),
            Courrier.statut_id == STATUT_TRAITE,
            or_(
                Courrier.agent_proprietaire_id == agent.id,
                Courrier.created_by == agent.id,
            ),
        )
    )

    # En copie : présent dans copies_courriers
    en_copie = await db.scalar(
        select(func.count(CopieCourrier.courrier_id))
        .join(Courrier, Courrier.id == CopieCourrier.courrier_id)
        .where(
            CopieCourrier.agent_id == agent.id,
            Courrier.tenant_id == agent.tenant_id,
            Courrier.supprime.is_(False),
        )
    )

    # En retard : statut != traite ET date_limite < today
    # ET (propriétaire = moi OU en copie)
    en_retard_proprio = await db.scalar(
        select(func.count(Courrier.id)).where(
            Courrier.tenant_id == agent.tenant_id,
            Courrier.supprime.is_(False),
            Courrier.statut_id != STATUT_TRAITE,
            Courrier.date_limite.is_not(None),
            Courrier.date_limite < aujourd_hui,
            Courrier.agent_proprietaire_id == agent.id,
        )
    )
    en_retard_copie = await db.scalar(
        select(func.count(CopieCourrier.courrier_id))
        .join(Courrier, Courrier.id == CopieCourrier.courrier_id)
        .where(
            CopieCourrier.agent_id == agent.id,
            Courrier.tenant_id == agent.tenant_id,
            Courrier.supprime.is_(False),
            Courrier.statut_id != STATUT_TRAITE,
            Courrier.date_limite.is_not(None),
            Courrier.date_limite < aujourd_hui,
        )
    )
    en_retard = int(en_retard_proprio or 0) + int(en_retard_copie or 0)

    corbeilles = [
        CompteurCorbeille(code="a_traiter", libelle="À traiter", compteur=int(a_traiter or 0)),
        CompteurCorbeille(code="traite", libelle="Traités", compteur=int(traite or 0)),
        CompteurCorbeille(code="en_copie", libelle="En copie", compteur=int(en_copie or 0)),
        CompteurCorbeille(code="en_retard", libelle="En retard", compteur=en_retard),
        CompteurCorbeille(code="a_valider", libelle="À valider", compteur=0, actif_en_06a=False),
        CompteurCorbeille(code="valides", libelle="Validés", compteur=0, actif_en_06a=False),
        CompteurCorbeille(
            code="a_faire_valider", libelle="À faire valider", compteur=0, actif_en_06a=False
        ),
        CompteurCorbeille(
            code="en_validation", libelle="En validation", compteur=0, actif_en_06a=False
        ),
    ]
    return CompteursCorbeilles(corbeilles=corbeilles)


# ============================================================================
# Lister + lire
# ============================================================================


def _appliquer_filtre_corbeille(
    base: "select", corbeille: str, agent_id: int, aujourd_hui: date_type
) -> "select":
    """Ajoute les conditions WHERE selon le code corbeille demandé."""
    if corbeille == "a_traiter":
        return base.where(
            Courrier.statut_id == STATUT_A_TRAITER,
            Courrier.agent_proprietaire_id == agent_id,
        )
    if corbeille == "traite":
        return base.where(
            Courrier.statut_id == STATUT_TRAITE,
            or_(
                Courrier.agent_proprietaire_id == agent_id,
                Courrier.created_by == agent_id,
            ),
        )
    if corbeille == "en_copie":
        # Sous-requête pour identifier les courriers où l'agent est en copie
        sous = select(CopieCourrier.courrier_id).where(
            CopieCourrier.agent_id == agent_id
        )
        return base.where(Courrier.id.in_(sous))
    if corbeille == "en_retard":
        sous_copie = select(CopieCourrier.courrier_id).where(
            CopieCourrier.agent_id == agent_id
        )
        return base.where(
            Courrier.statut_id != STATUT_TRAITE,
            Courrier.date_limite.is_not(None),
            Courrier.date_limite < aujourd_hui,
            or_(
                Courrier.agent_proprietaire_id == agent_id,
                Courrier.id.in_(sous_copie),
            ),
        )
    # Corbeilles 5-8 : différées à 06B, on retourne 0 résultat
    return base.where(False)  # type: ignore[arg-type]


@router.get("", response_model=list[CourrierLecture])
async def lister(
    agent: AgentCourant,
    db: SessionDB,
    corbeille: str = Query(
        "a_traiter",
        description="Code de la corbeille à afficher",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[Courrier]:
    aujourd_hui = date_type.today()
    base = (
        select(Courrier)
        .where(
            Courrier.tenant_id == agent.tenant_id,
            Courrier.supprime.is_(False),
        )
        .order_by(Courrier.date_limite.asc().nulls_last(), Courrier.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    base = _appliquer_filtre_corbeille(base, corbeille, agent.id, aujourd_hui)
    result = await db.execute(base)
    return list(result.scalars().unique())


@router.get("/{courrier_id}", response_model=CourrierDetail)
async def lire(
    courrier_id: int, agent: AgentCourant, db: SessionDB
) -> CourrierDetail:
    courrier = await _charger_courrier(db, courrier_id, agent.tenant_id)

    if not await _agent_voit_courrier(db, courrier, agent.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé à ce courrier"
        )

    # Copies
    res_copies = await db.execute(
        select(Agent).join(CopieCourrier, CopieCourrier.agent_id == Agent.id).where(
            CopieCourrier.courrier_id == courrier.id
        )
    )
    copies = [AgentResume.model_validate(a) for a in res_copies.scalars()]

    # Notes (récentes d'abord)
    res_notes = await db.execute(
        select(NoteCourrier)
        .where(NoteCourrier.courrier_id == courrier.id)
        .order_by(NoteCourrier.created_at.desc())
    )
    notes = [NoteLecture.model_validate(n) for n in res_notes.scalars()]

    # Historique
    res_histo = await db.execute(
        select(HistoriqueCourrier)
        .where(HistoriqueCourrier.courrier_id == courrier.id)
        .order_by(HistoriqueCourrier.ts.desc())
    )
    historique = [HistoriqueLecture.model_validate(h) for h in res_histo.scalars()]

    # Pièces additionnelles
    res_pieces = await db.execute(
        select(DocumentCourrier.document_id).where(
            DocumentCourrier.courrier_id == courrier.id
        )
    )
    pieces = [int(x) for x in res_pieces.scalars()]

    # Construction du DocumentDetail (CourrierLecture + extras)
    lecture = CourrierLecture.model_validate(courrier)
    return CourrierDetail(
        **lecture.model_dump(),
        copies=copies,
        notes=notes,
        historique=historique,
        pieces_additionnelles=pieces,
    )


# ============================================================================
# Création
# ============================================================================


@router.post("", response_model=CourrierLecture, status_code=status.HTTP_201_CREATED)
async def creer(
    agent: AgentCourant,
    db: SessionDB,
    request: Request,
    ip: IpClient,
    metadonnees: Annotated[str, Form(description="JSON CourrierCreation")],
    fichier: Annotated[UploadFile, File(description="Pièce principale obligatoire")],
) -> Courrier:
    """Crée un courrier (multipart : pièce principale + JSON métadonnées).

    La pièce principale crée un Document via le pipeline de PRD-02.
    """
    # 1. Parser les métadonnées
    try:
        body = CourrierCreation.model_validate(json.loads(metadonnees))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Métadonnées invalides : {exc}",
        ) from exc

    # 2. Vérifications métier
    if body.sens in ("entrant", "sortant") and body.correspondant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un courrier entrant ou sortant doit avoir un correspondant.",
        )

    # Vérifier le correspondant appartient au tenant si fourni
    if body.correspondant_id is not None:
        existe = await db.scalar(
            select(func.count(Correspondant.id)).where(
                Correspondant.id == body.correspondant_id,
                Correspondant.tenant_id == agent.tenant_id,
            )
        )
        if not existe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Correspondant introuvable",
            )

    # Vérifier l'agent destinataire appartient au tenant
    dest = await db.scalar(
        select(func.count(Agent.id)).where(
            Agent.id == body.agent_destinataire_id,
            Agent.tenant_id == agent.tenant_id,
            Agent.actif.is_(True),
        )
    )
    if not dest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent destinataire introuvable",
        )

    # 3. Lire + chiffrer la pièce principale
    settings = get_settings()
    contenu = await fichier.read()
    if len(contenu) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.max_upload_size_mb} Mo)",
        )

    stocke = await stocker(contenu, tenant_id=agent.tenant_id)

    # Déduplication par checksum
    res_existant = await db.execute(
        select(Document).where(
            Document.tenant_id == agent.tenant_id,
            Document.checksum_sha256 == stocke.checksum_sha256,
            Document.supprime.is_(False),
        )
    )
    document = res_existant.scalar_one_or_none()
    if document is None:
        document = Document(
            tenant_id=agent.tenant_id,
            titre=body.document_titre,
            mime=stocke.mime,
            taille_octets=stocke.taille_octets,
            checksum_sha256=stocke.checksum_sha256,
            chemin_stockage=stocke.chemin_relatif,
            nonce=stocke.nonce,
            categorie_id=body.document_categorie_id,
            origine="courrier",
            statut="pret",
            created_by=agent.id,
        )
        db.add(document)
        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflit lors de la création du document.",
            ) from exc

    # 4. Générer le numéro d'enregistrement (advisory lock)
    numero = await prochain_numero_enregistrement(db, agent.tenant_id)

    # 5. Créer le courrier
    courrier = Courrier(
        tenant_id=agent.tenant_id,
        numero_enregistrement=numero,
        sens=body.sens,
        ref_externe=body.ref_externe,
        categorie_id=body.categorie_id,
        objet=body.objet,
        mots_cles=body.mots_cles,
        observations=body.observations,
        date_courrier=body.date_courrier or date_type.today(),
        date_arrivee=body.date_arrivee
        if body.sens == "entrant"
        else None,
        date_limite=body.date_limite,
        correspondant_id=body.correspondant_id,
        departement_destinataire_id=body.departement_destinataire_id,
        agent_destinataire_id=body.agent_destinataire_id,
        document_principal_id=document.id,
        statut_id=STATUT_A_TRAITER,
        agent_proprietaire_id=body.agent_destinataire_id,
        created_by=agent.id,
    )
    db.add(courrier)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflit lors de la création : {exc.orig}",
        ) from exc

    # 6. Historique + audit
    await _ajouter_historique(
        db,
        courrier.id,
        agent.id,
        ACTION_CREATION,
        {"sens": body.sens, "destinataire_id": body.agent_destinataire_id},
    )
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="courrier.create",
        entite="courriers",
        entite_id=courrier.id,
        payload={"numero": numero, "sens": body.sens},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )

    await db.commit()
    await db.refresh(courrier)

    # 7. Notification email asynchrone (fire-and-forget)
    if body.agent_destinataire_id != agent.id:
        await notifier_nouveau_courrier(
            courrier_id=courrier.id,
            agent_destinataire_id=body.agent_destinataire_id,
            tenant_id=agent.tenant_id,
        )

    return courrier


# ============================================================================
# Actions sur un courrier (PRD-06A §5.5 à §5.10)
# ============================================================================


@router.post("/{courrier_id}/copies", response_model=CourrierDetail)
async def faire_une_copie(
    courrier_id: int,
    body: CopieBody,
    agent: AgentCourant,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> CourrierDetail:
    """Met le courrier en copie pour N agents."""
    courrier = await _charger_courrier(db, courrier_id, agent.tenant_id)
    if courrier.statut_id == STATUT_TRAITE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de mettre en copie un courrier déjà traité.",
        )
    if not await _agent_voit_courrier(db, courrier, agent.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé"
        )

    # Vérifier que les agents cibles appartiennent au tenant
    res_agents = await db.execute(
        select(Agent.id).where(
            Agent.id.in_(body.agent_ids),
            Agent.tenant_id == agent.tenant_id,
            Agent.actif.is_(True),
        )
    )
    ids_valides = {int(x) for x in res_agents.scalars()}
    ids_demandes = set(body.agent_ids)
    if ids_valides != ids_demandes:
        manquants = ids_demandes - ids_valides
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent(s) introuvable(s) ou inactif(s) : {sorted(manquants)}",
        )

    # Agents déjà en copie (on ne les recréera pas)
    res_deja = await db.execute(
        select(CopieCourrier.agent_id).where(
            CopieCourrier.courrier_id == courrier.id,
            CopieCourrier.agent_id.in_(body.agent_ids),
        )
    )
    deja = {int(x) for x in res_deja.scalars()}
    ajoutes = sorted(ids_demandes - deja - {courrier.agent_proprietaire_id})

    for agent_id in ajoutes:
        db.add(
            CopieCourrier(
                courrier_id=courrier.id, agent_id=agent_id, ajoute_par=agent.id
            )
        )

    if ajoutes:
        await _ajouter_historique(
            db, courrier.id, agent.id, ACTION_COPIE, {"agents": ajoutes}
        )
        await journaliser(
            db,
            tenant_id=agent.tenant_id,
            agent_id=agent.id,
            action="courrier.copie",
            entite="courriers",
            entite_id=courrier.id,
            payload={"agents": ajoutes},
            ip=ip,
            user_agent=request.headers.get("user-agent"),
        )

    await db.commit()
    return await lire(courrier.id, agent, db)


@router.post("/{courrier_id}/imputer", response_model=CourrierDetail)
async def imputer(
    courrier_id: int,
    body: ImputerBody,
    agent: AgentCourant,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> CourrierDetail:
    """Transfère la propriété à un autre agent. L'imputeur passe en copie."""
    courrier = await _charger_courrier(db, courrier_id, agent.tenant_id)
    if courrier.statut_id == STATUT_TRAITE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible d'imputer un courrier déjà traité.",
        )
    if courrier.agent_proprietaire_id != agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le propriétaire actuel peut imputer le courrier.",
        )

    # Vérifier l'agent destinataire
    cible = await db.scalar(
        select(Agent).where(
            Agent.id == body.agent_impute_id,
            Agent.tenant_id == agent.tenant_id,
            Agent.actif.is_(True),
        )
    )
    if cible is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent destinataire introuvable",
        )
    if body.agent_impute_id == agent.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tu es déjà propriétaire de ce courrier.",
        )

    ancien_proprio = courrier.agent_proprietaire_id

    # Transfert
    courrier.agent_proprietaire_id = body.agent_impute_id

    # Ajout ancien proprio en copie (s'il n'y est pas déjà)
    deja_en_copie = await db.scalar(
        select(func.count(CopieCourrier.agent_id)).where(
            CopieCourrier.courrier_id == courrier.id,
            CopieCourrier.agent_id == ancien_proprio,
        )
    )
    if not deja_en_copie:
        db.add(
            CopieCourrier(
                courrier_id=courrier.id, agent_id=ancien_proprio, ajoute_par=agent.id
            )
        )

    # Ligne d'imputation
    db.add(
        Imputation(
            courrier_id=courrier.id,
            agent_imputeur_id=agent.id,
            agent_impute_id=body.agent_impute_id,
            instruction=body.instruction,
        )
    )

    await _ajouter_historique(
        db,
        courrier.id,
        agent.id,
        ACTION_IMPUTATION,
        {
            "agent_impute_id": body.agent_impute_id,
            "ancien_proprietaire_id": ancien_proprio,
        },
    )
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="courrier.imputation",
        entite="courriers",
        entite_id=courrier.id,
        payload={"agent_impute_id": body.agent_impute_id},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    # Notification au nouvel imputé
    await notifier_nouveau_courrier(
        courrier_id=courrier.id,
        agent_destinataire_id=body.agent_impute_id,
        tenant_id=agent.tenant_id,
    )

    return await lire(courrier.id, agent, db)


@router.post(
    "/{courrier_id}/envoyer",
    response_model=CourrierLecture,
    summary="Clôturer (passe le statut à traité)",
)
async def envoyer(
    courrier_id: int,
    agent: AgentCourant,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Courrier:
    courrier = await _charger_courrier(db, courrier_id, agent.tenant_id)
    if courrier.agent_proprietaire_id != agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le propriétaire peut envoyer (clôturer) le courrier.",
        )
    if courrier.statut_id == STATUT_TRAITE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Courrier déjà clôturé.",
        )
    courrier.statut_id = STATUT_TRAITE
    await _ajouter_historique(db, courrier.id, agent.id, ACTION_ENVOI)
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="courrier.envoi",
        entite="courriers",
        entite_id=courrier.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(courrier)
    return courrier


@router.post(
    "/{courrier_id}/notes",
    response_model=NoteLecture,
    status_code=status.HTTP_201_CREATED,
)
async def ajouter_note(
    courrier_id: int,
    body: NoteCreation,
    agent: AgentCourant,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> NoteCourrier:
    courrier = await _charger_courrier(db, courrier_id, agent.tenant_id)
    if not await _agent_voit_courrier(db, courrier, agent.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé"
        )
    note = NoteCourrier(
        courrier_id=courrier.id, agent_id=agent.id, contenu=body.contenu
    )
    db.add(note)
    await _ajouter_historique(
        db, courrier.id, agent.id, ACTION_NOTE, {"contenu_court": body.contenu[:80]}
    )
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="courrier.note",
        entite="courriers",
        entite_id=courrier.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(note)
    return note


@router.post("/{courrier_id}/documents", response_model=CourrierDetail)
async def ajouter_piece(
    courrier_id: int,
    agent: AgentCourant,
    db: SessionDB,
    request: Request,
    ip: IpClient,
    fichier: Annotated[UploadFile, File(...)],
    titre: Annotated[str, Form(min_length=1, max_length=512)],
    categorie_id: Annotated[int, Form(...)],
) -> CourrierDetail:
    """Ajoute une pièce additionnelle (multipart simple : fichier + titre + catégorie)."""
    courrier = await _charger_courrier(db, courrier_id, agent.tenant_id)
    if courrier.statut_id == STATUT_TRAITE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible d'ajouter une pièce à un courrier déjà traité.",
        )
    if not await _agent_voit_courrier(db, courrier, agent.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé"
        )

    settings = get_settings()
    contenu = await fichier.read()
    if len(contenu) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.max_upload_size_mb} Mo)",
        )

    stocke = await stocker(contenu, tenant_id=agent.tenant_id)

    # Déduplication
    res_existant = await db.execute(
        select(Document).where(
            Document.tenant_id == agent.tenant_id,
            Document.checksum_sha256 == stocke.checksum_sha256,
            Document.supprime.is_(False),
        )
    )
    document = res_existant.scalar_one_or_none()
    if document is None:
        document = Document(
            tenant_id=agent.tenant_id,
            titre=titre,
            mime=stocke.mime,
            taille_octets=stocke.taille_octets,
            checksum_sha256=stocke.checksum_sha256,
            chemin_stockage=stocke.chemin_relatif,
            nonce=stocke.nonce,
            categorie_id=categorie_id,
            origine="courrier",
            statut="pret",
            created_by=agent.id,
        )
        db.add(document)
        await db.flush()

    # Lien M:N (ignorer si déjà lié)
    deja = await db.scalar(
        select(func.count(DocumentCourrier.document_id)).where(
            DocumentCourrier.courrier_id == courrier.id,
            DocumentCourrier.document_id == document.id,
        )
    )
    if not deja:
        db.add(
            DocumentCourrier(
                courrier_id=courrier.id,
                document_id=document.id,
                ajoute_par=agent.id,
            )
        )

    await _ajouter_historique(
        db,
        courrier.id,
        agent.id,
        ACTION_AJOUT_DOCUMENT,
        {"document_id": document.id, "titre": titre},
    )
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="courrier.ajout_document",
        entite="courriers",
        entite_id=courrier.id,
        payload={"document_id": document.id},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    return await lire(courrier.id, agent, db)


@router.post("/{courrier_id}/repondre", response_model=CourrierLecture)
async def repondre(
    courrier_id: int,
    agent: AgentCourant,
    db: SessionDB,
    request: Request,
    ip: IpClient,
    metadonnees: Annotated[str, Form(description="JSON RepondreBody")],
    fichier: Annotated[UploadFile, File(...)],
) -> Courrier:
    """Crée un courrier sortant lié au courrier d'origine (réponse)."""
    origine = await _charger_courrier(db, courrier_id, agent.tenant_id)
    if origine.statut_id == STATUT_TRAITE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de répondre à un courrier déjà clôturé.",
        )
    if not await _agent_voit_courrier(db, origine, agent.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé"
        )

    try:
        body = RepondreBody.model_validate(json.loads(metadonnees))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Métadonnées invalides : {exc}",
        ) from exc

    # Stocker la pièce
    settings = get_settings()
    contenu = await fichier.read()
    if len(contenu) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fichier trop volumineux",
        )
    stocke = await stocker(contenu, tenant_id=agent.tenant_id)
    res_existant = await db.execute(
        select(Document).where(
            Document.tenant_id == agent.tenant_id,
            Document.checksum_sha256 == stocke.checksum_sha256,
            Document.supprime.is_(False),
        )
    )
    document = res_existant.scalar_one_or_none()
    if document is None:
        document = Document(
            tenant_id=agent.tenant_id,
            titre=body.document_titre,
            mime=stocke.mime,
            taille_octets=stocke.taille_octets,
            checksum_sha256=stocke.checksum_sha256,
            chemin_stockage=stocke.chemin_relatif,
            nonce=stocke.nonce,
            categorie_id=body.document_categorie_id,
            origine="courrier",
            statut="pret",
            created_by=agent.id,
        )
        db.add(document)
        await db.flush()

    numero = await prochain_numero_enregistrement(db, agent.tenant_id)
    correspondant_id = body.correspondant_id or origine.correspondant_id

    # Calcul automatique du destinataire de la réponse :
    # - si je suis l'agent à qui ce courrier a été imputé en dernier,
    #   la réponse remonte à l'imputeur (mon supérieur fonctionnel)
    # - sinon (je suis le propriétaire d'origine), elle reste à moi
    # - le body peut forcer un destinataire explicite (superviseur, cas
    #   particulier).
    if body.agent_destinataire_id is not None:
        destinataire_id = body.agent_destinataire_id
    else:
        res_imp = await db.execute(
            select(Imputation.agent_imputeur_id)
            .where(
                Imputation.courrier_id == origine.id,
                Imputation.agent_impute_id == agent.id,
            )
            .order_by(Imputation.ts.desc())
            .limit(1)
        )
        imputeur_id = res_imp.scalar_one_or_none()
        destinataire_id = imputeur_id if imputeur_id is not None else agent.id

    reponse = Courrier(
        tenant_id=agent.tenant_id,
        numero_enregistrement=numero,
        sens="sortant",
        categorie_id=origine.categorie_id,
        objet=body.objet,
        mots_cles=body.mots_cles,
        observations=body.observations,
        date_courrier=date_type.today(),
        date_limite=body.date_limite,
        correspondant_id=correspondant_id,
        departement_destinataire_id=body.departement_destinataire_id,
        agent_destinataire_id=destinataire_id,
        document_principal_id=document.id,
        statut_id=STATUT_A_TRAITER,
        agent_proprietaire_id=destinataire_id,
        courrier_origine_id=origine.id,
        created_by=agent.id,
    )
    db.add(reponse)
    await db.flush()

    # Répondre = traiter le courrier d'origine. Il sort des corbeilles
    # "À traiter" / "En retard" et passe en "Traités".
    origine.statut_id = STATUT_TRAITE

    await _ajouter_historique(
        db,
        origine.id,
        agent.id,
        ACTION_REPONSE,
        {"reponse_id": reponse.id, "numero": numero},
    )
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="courrier.reponse",
        entite="courriers",
        entite_id=origine.id,
        payload={"reponse_id": reponse.id},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(reponse)

    if destinataire_id != agent.id:
        await notifier_nouveau_courrier(
            courrier_id=reponse.id,
            agent_destinataire_id=destinataire_id,
            tenant_id=agent.tenant_id,
        )

    return reponse


@router.delete("/{courrier_id}", response_model=CourrierLecture)
async def supprimer(
    courrier_id: int,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Courrier:
    """Soft delete (superviseur uniquement)."""
    courrier = await _charger_courrier(db, courrier_id, superviseur.tenant_id)
    courrier.supprime = True
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="courrier.delete",
        entite="courriers",
        entite_id=courrier.id,
        payload={"numero": courrier.numero_enregistrement},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(courrier)
    return courrier
