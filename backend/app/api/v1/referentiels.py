"""Routes des référentiels documentaires (PRD-02).

- Lecture ouverte à tous les agents connectés.
- Création :
    - Catégories : archivistes et superviseurs (RG-2 § 5.10 PRD-02 — à la volée
      depuis le formulaire d'upload).
    - Thématiques et types : superviseurs uniquement.
- Modification / désactivation : superviseur uniquement.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import (
    AgentArchivisteOuPlus,
    AgentCourant,
    AgentSuperviseur,
    IpClient,
    SessionDB,
)
from app.models import Categorie, Document, Thematique, TypeDocument
from app.schemas.referentiel import (
    CategorieCreation,
    CategorieLecture,
    CategorieMiseAJour,
    ReferentielCreation,
    ReferentielLecture,
    ReferentielMiseAJour,
)
from app.services.audit import journaliser

router = APIRouter(tags=["referentiels"])


# ---------------------------------------------------------------------------
# Catégories
# ---------------------------------------------------------------------------


@router.get(
    "/categories",
    response_model=list[CategorieLecture],
    summary="Lister les catégories du tenant",
)
async def lister_categories(
    agent: AgentCourant, db: SessionDB
) -> list[Categorie]:
    result = await db.execute(
        select(Categorie)
        .where(Categorie.tenant_id == agent.tenant_id, Categorie.actif.is_(True))
        .order_by(Categorie.libelle)
    )
    return list(result.scalars())


@router.post(
    "/categories",
    response_model=CategorieLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une catégorie (archiviste ou superviseur — à la volée OK)",
)
async def creer_categorie(
    body: CategorieCreation,
    agent: AgentArchivisteOuPlus,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Categorie:
    cat = Categorie(
        tenant_id=agent.tenant_id,
        libelle=body.libelle,
        description=body.description,
    )
    db.add(cat)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Libellé de catégorie déjà utilisé dans ce tenant",
        ) from exc

    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="categorie.create",
        entite="categories",
        entite_id=cat.id,
        payload={"libelle": body.libelle},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(cat)
    return cat


# ---------------------------------------------------------------------------
# Thématiques
# ---------------------------------------------------------------------------


@router.get(
    "/thematiques",
    response_model=list[ReferentielLecture],
    summary="Lister les thématiques du tenant",
)
async def lister_thematiques(
    agent: AgentCourant, db: SessionDB
) -> list[Thematique]:
    result = await db.execute(
        select(Thematique)
        .where(Thematique.tenant_id == agent.tenant_id, Thematique.actif.is_(True))
        .order_by(Thematique.libelle)
    )
    return list(result.scalars())


@router.post(
    "/thematiques",
    response_model=ReferentielLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une thématique (superviseur)",
)
async def creer_thematique(
    body: ReferentielCreation,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Thematique:
    th = Thematique(tenant_id=superviseur.tenant_id, libelle=body.libelle)
    db.add(th)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Libellé de thématique déjà utilisé dans ce tenant",
        ) from exc

    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="thematique.create",
        entite="thematiques",
        entite_id=th.id,
        payload={"libelle": body.libelle},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(th)
    return th


# ---------------------------------------------------------------------------
# Types de document
# ---------------------------------------------------------------------------


@router.get(
    "/types-document",
    response_model=list[ReferentielLecture],
    summary="Lister les types de document du tenant",
)
async def lister_types(agent: AgentCourant, db: SessionDB) -> list[TypeDocument]:
    result = await db.execute(
        select(TypeDocument)
        .where(TypeDocument.tenant_id == agent.tenant_id, TypeDocument.actif.is_(True))
        .order_by(TypeDocument.libelle)
    )
    return list(result.scalars())


@router.post(
    "/types-document",
    response_model=ReferentielLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un type de document (superviseur)",
)
async def creer_type(
    body: ReferentielCreation,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> TypeDocument:
    t = TypeDocument(tenant_id=superviseur.tenant_id, libelle=body.libelle)
    db.add(t)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Libellé de type de document déjà utilisé dans ce tenant",
        ) from exc

    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="type_document.create",
        entite="types_document",
        entite_id=t.id,
        payload={"libelle": body.libelle},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(t)
    return t


# ===========================================================================
# Mise à jour et désactivation — superviseur uniquement
# ===========================================================================


async def _charger_categorie(db, cat_id: int, tenant_id: int) -> Categorie:
    result = await db.execute(
        select(Categorie).where(Categorie.id == cat_id, Categorie.tenant_id == tenant_id)
    )
    c = result.scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable")
    return c


async def _charger_thematique(db, th_id: int, tenant_id: int) -> Thematique:
    result = await db.execute(
        select(Thematique).where(Thematique.id == th_id, Thematique.tenant_id == tenant_id)
    )
    t = result.scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thématique introuvable")
    return t


async def _charger_type(db, t_id: int, tenant_id: int) -> TypeDocument:
    result = await db.execute(
        select(TypeDocument).where(TypeDocument.id == t_id, TypeDocument.tenant_id == tenant_id)
    )
    t = result.scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Type introuvable")
    return t


async def _flush_409_libelle(db, label: str) -> None:
    """Flush + 409 lisible sur violation UNIQUE (libellé déjà utilisé)."""
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Libellé de {label} déjà utilisé dans ce tenant",
        ) from exc


# ----- Catégories ---------------------------------------------------------


@router.put(
    "/categories/{cat_id}",
    response_model=CategorieLecture,
    summary="Modifier une catégorie (superviseur)",
)
async def maj_categorie(
    cat_id: int,
    body: CategorieMiseAJour,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Categorie:
    cat = await _charger_categorie(db, cat_id, superviseur.tenant_id)
    diff: dict[str, object] = {}
    if body.libelle is not None and body.libelle != cat.libelle:
        diff["libelle"] = body.libelle
        cat.libelle = body.libelle
    if body.description is not None and body.description != cat.description:
        diff["description"] = body.description
        cat.description = body.description
    if not diff:
        return cat

    await _flush_409_libelle(db, "catégorie")
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="categorie.update",
        entite="categories",
        entite_id=cat.id,
        payload={"diff": diff},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete(
    "/categories/{cat_id}",
    response_model=CategorieLecture,
    summary="Désactiver une catégorie (superviseur) — bloqué si documents liés",
)
async def desactiver_categorie(
    cat_id: int,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Categorie:
    cat = await _charger_categorie(db, cat_id, superviseur.tenant_id)
    nb = await db.scalar(
        select(func.count(Document.id)).where(
            Document.categorie_id == cat.id, Document.supprime.is_(False)
        )
    )
    if nb and int(nb) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Impossible de désactiver : {int(nb)} document(s) "
                "utilisent cette catégorie. Réaffecte-les d'abord."
            ),
        )
    if not cat.actif:
        return cat
    cat.actif = False
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="categorie.desactiver",
        entite="categories",
        entite_id=cat.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(cat)
    return cat


# ----- Thématiques --------------------------------------------------------


@router.put(
    "/thematiques/{th_id}",
    response_model=ReferentielLecture,
    summary="Renommer une thématique (superviseur)",
)
async def maj_thematique(
    th_id: int,
    body: ReferentielMiseAJour,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Thematique:
    th = await _charger_thematique(db, th_id, superviseur.tenant_id)
    if body.libelle == th.libelle:
        return th
    ancien = th.libelle
    th.libelle = body.libelle
    await _flush_409_libelle(db, "thématique")
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="thematique.update",
        entite="thematiques",
        entite_id=th.id,
        payload={"diff": {"libelle": [ancien, body.libelle]}},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(th)
    return th


@router.delete(
    "/thematiques/{th_id}",
    response_model=ReferentielLecture,
    summary="Désactiver une thématique (superviseur)",
)
async def desactiver_thematique(
    th_id: int,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Thematique:
    th = await _charger_thematique(db, th_id, superviseur.tenant_id)
    nb = await db.scalar(
        select(func.count(Document.id)).where(
            Document.thematique_id == th.id, Document.supprime.is_(False)
        )
    )
    if nb and int(nb) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Impossible de désactiver : {int(nb)} document(s) "
                "référencent cette thématique."
            ),
        )
    if not th.actif:
        return th
    th.actif = False
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="thematique.desactiver",
        entite="thematiques",
        entite_id=th.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(th)
    return th


# ----- Types de document --------------------------------------------------


@router.put(
    "/types-document/{t_id}",
    response_model=ReferentielLecture,
    summary="Renommer un type de document (superviseur)",
)
async def maj_type(
    t_id: int,
    body: ReferentielMiseAJour,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> TypeDocument:
    t = await _charger_type(db, t_id, superviseur.tenant_id)
    if body.libelle == t.libelle:
        return t
    ancien = t.libelle
    t.libelle = body.libelle
    await _flush_409_libelle(db, "type de document")
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="type_document.update",
        entite="types_document",
        entite_id=t.id,
        payload={"diff": {"libelle": [ancien, body.libelle]}},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(t)
    return t


@router.delete(
    "/types-document/{t_id}",
    response_model=ReferentielLecture,
    summary="Désactiver un type de document (superviseur)",
)
async def desactiver_type(
    t_id: int,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> TypeDocument:
    t = await _charger_type(db, t_id, superviseur.tenant_id)
    nb = await db.scalar(
        select(func.count(Document.id)).where(
            Document.type_document_id == t.id, Document.supprime.is_(False)
        )
    )
    if nb and int(nb) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Impossible de désactiver : {int(nb)} document(s) "
                "référencent ce type."
            ),
        )
    if not t.actif:
        return t
    t.actif = False
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="type_document.desactiver",
        entite="types_document",
        entite_id=t.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(t)
    return t
