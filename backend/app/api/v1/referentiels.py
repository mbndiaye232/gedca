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
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import (
    AgentArchivisteOuPlus,
    AgentCourant,
    AgentSuperviseur,
    IpClient,
    SessionDB,
)
from app.models import Categorie, Thematique, TypeDocument
from app.schemas.referentiel import (
    CategorieCreation,
    CategorieLecture,
    ReferentielCreation,
    ReferentielLecture,
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
