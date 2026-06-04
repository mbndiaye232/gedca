"""Routes de gestion des départements (services de l'organisation)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import (
    AgentCourant,
    AgentSuperviseur,
    IpClient,
    SessionDB,
)
from app.models import Agent, Departement
from app.schemas.departement import (
    DepartementCreation,
    DepartementLecture,
    DepartementMiseAJour,
)
from app.services.audit import journaliser

router = APIRouter(prefix="/departements", tags=["departements"])


@router.get(
    "",
    response_model=list[DepartementLecture],
    summary="Lister les départements du tenant",
)
async def lister(agent: AgentCourant, db: SessionDB) -> list[Departement]:
    result = await db.execute(
        select(Departement)
        .where(Departement.tenant_id == agent.tenant_id, Departement.actif.is_(True))
        .order_by(Departement.libelle)
    )
    return list(result.scalars())


@router.post(
    "",
    response_model=DepartementLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un département (superviseur)",
)
async def creer(
    body: DepartementCreation,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Departement:
    dep = Departement(
        tenant_id=superviseur.tenant_id, code=body.code, libelle=body.libelle
    )
    db.add(dep)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Libellé de département déjà utilisé dans ce tenant",
        ) from exc

    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="departement.create",
        entite="departements",
        entite_id=dep.id,
        payload={"libelle": body.libelle},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(dep)
    return dep


@router.put(
    "/{dep_id}",
    response_model=DepartementLecture,
    summary="Modifier un département (superviseur)",
)
async def maj(
    dep_id: int,
    body: DepartementMiseAJour,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Departement:
    dep = await _charger(db, dep_id, superviseur.tenant_id)
    diff: dict[str, object] = {}
    if body.code is not None and body.code != dep.code:
        diff["code"] = body.code
        dep.code = body.code
    if body.libelle is not None and body.libelle != dep.libelle:
        diff["libelle"] = body.libelle
        dep.libelle = body.libelle

    if not diff:
        return dep

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Libellé déjà utilisé dans ce tenant",
        ) from exc

    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="departement.update",
        entite="departements",
        entite_id=dep.id,
        payload={"diff": diff},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(dep)
    return dep


@router.delete(
    "/{dep_id}",
    response_model=DepartementLecture,
    summary="Désactiver un département (superviseur) — bloqué si agents actifs",
)
async def desactiver(
    dep_id: int,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Departement:
    dep = await _charger(db, dep_id, superviseur.tenant_id)

    # Vérifier qu'aucun agent actif n'y est rattaché
    nb_agents = await db.scalar(
        select(func.count(Agent.id)).where(
            Agent.departement_id == dep.id, Agent.actif.is_(True)
        )
    )
    if nb_agents and nb_agents > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Impossible de désactiver : {nb_agents} agent(s) actif(s) "
                "dans ce département. Réaffecte-les d'abord."
            ),
        )

    if not dep.actif:
        return dep  # idempotent

    dep.actif = False
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="departement.desactiver",
        entite="departements",
        entite_id=dep.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(dep)
    return dep


async def _charger(db, dep_id: int, tenant_id: int) -> Departement:
    result = await db.execute(
        select(Departement).where(
            Departement.id == dep_id, Departement.tenant_id == tenant_id
        )
    )
    dep = result.scalar_one_or_none()
    if dep is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Département introuvable"
        )
    return dep
