"""Routes de gestion des agents.

- `/me`     : self-service (lecture, modification de son profil)
- `/`       : superviseur uniquement (liste, création)
- `/{id}`   : superviseur uniquement (détail, modification, désactivation)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.api.deps import (
    AgentCourant,
    AgentSuperviseur,
    IpClient,
    SessionDB,
)
from app.models import Agent
from app.schemas.agent import (
    AgentCreation,
    AgentLecture,
    AgentMiseAJour,
    MonProfilMiseAJour,
)
from app.services.audit import journaliser
from app.services.password import hacher_mot_de_passe, verifier_mot_de_passe

router = APIRouter(prefix="/agents", tags=["agents"])


# ----- Self-service -----------------------------------------------------------


@router.get("/me", response_model=AgentLecture, summary="Profil de l'agent connecté")
async def lire_mon_profil(agent: AgentCourant) -> Agent:
    return agent


@router.put(
    "/me",
    response_model=AgentLecture,
    summary="Modifier son propre profil (email, téléphone, photo, mot de passe)",
)
async def maj_mon_profil(
    body: MonProfilMiseAJour,
    agent: AgentCourant,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Agent:
    # Champs simples
    if body.email is not None:
        agent.email = body.email
    if body.telephone is not None:
        agent.telephone = body.telephone
    if body.photo_chemin is not None:
        agent.photo_chemin = body.photo_chemin

    # Changement de mot de passe — exige l'ancien
    if body.nouveau_mot_de_passe is not None:
        if body.mot_de_passe_actuel is None or not verifier_mot_de_passe(
            body.mot_de_passe_actuel, agent.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mot de passe actuel incorrect",
            )
        agent.password_hash = hacher_mot_de_passe(body.nouveau_mot_de_passe)
        await journaliser(
            db,
            tenant_id=agent.tenant_id,
            agent_id=agent.id,
            action="agent.password_change",
            entite="agents",
            entite_id=agent.id,
            payload={"par_soi_meme": True},
            ip=ip,
            user_agent=request.headers.get("user-agent"),
        )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email déjà utilisé par un autre agent",
        ) from exc
    await db.refresh(agent)
    return agent


# ----- Routes superviseur -----------------------------------------------------


@router.get(
    "",
    response_model=list[AgentLecture],
    summary="Lister les agents du tenant (superviseur)",
)
async def lister_agents(superviseur: AgentSuperviseur, db: SessionDB) -> list[Agent]:
    result = await db.execute(
        select(Agent)
        .where(Agent.tenant_id == superviseur.tenant_id)
        .order_by(Agent.nom, Agent.prenom)
    )
    return list(result.scalars())


@router.post(
    "",
    response_model=AgentLecture,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un agent (superviseur)",
)
async def creer_agent(
    body: AgentCreation,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Agent:
    nouvel_agent = Agent(
        tenant_id=superviseur.tenant_id,
        login=body.login,
        password_hash=hacher_mot_de_passe(body.mot_de_passe),
        auth_provider="local",
        nom=body.nom,
        prenom=body.prenom,
        email=body.email,
        telephone=body.telephone,
        fonction=body.fonction,
        departement_id=body.departement_id,
        role_id=body.role_id,
        actif=True,
    )
    db.add(nouvel_agent)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Login ou email déjà utilisé dans ce tenant",
        ) from exc

    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="agent.create",
        entite="agents",
        entite_id=nouvel_agent.id,
        payload={"login": body.login, "role_id": body.role_id},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(nouvel_agent)
    return nouvel_agent


@router.get(
    "/{agent_id}",
    response_model=AgentLecture,
    summary="Détail d'un agent (superviseur)",
)
async def lire_agent(
    agent_id: int, superviseur: AgentSuperviseur, db: SessionDB
) -> Agent:
    agent = await _charger_agent_du_tenant(db, agent_id, superviseur.tenant_id)
    return agent


@router.put(
    "/{agent_id}",
    response_model=AgentLecture,
    summary="Modifier un agent (superviseur)",
)
async def maj_agent(
    agent_id: int,
    body: AgentMiseAJour,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Agent:
    agent = await _charger_agent_du_tenant(db, agent_id, superviseur.tenant_id)
    diff: dict[str, object] = {}
    for champ in ("nom", "prenom", "email", "telephone", "fonction", "departement_id", "role_id"):
        nouvelle = getattr(body, champ)
        if nouvelle is not None and nouvelle != getattr(agent, champ):
            diff[champ] = nouvelle
            setattr(agent, champ, nouvelle)

    if not diff:
        return agent

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email déjà utilisé dans ce tenant",
        ) from exc

    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="agent.update",
        entite="agents",
        entite_id=agent.id,
        payload={"diff": diff},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(agent)
    return agent


@router.post(
    "/{agent_id}/desactiver",
    response_model=AgentLecture,
    summary="Désactiver un agent (superviseur)",
)
async def desactiver_agent(
    agent_id: int,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Agent:
    agent = await _charger_agent_du_tenant(db, agent_id, superviseur.tenant_id)

    if agent.id == superviseur.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un superviseur ne peut pas se désactiver lui-même",
        )

    if not agent.actif:
        return agent  # idempotent

    agent.actif = False
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="agent.desactiver",
        entite="agents",
        entite_id=agent.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(agent)
    return agent


# ----- Helpers internes -------------------------------------------------------


async def _charger_agent_du_tenant(
    db, agent_id: int, tenant_id: int
) -> Agent:
    """Charge un agent en vérifiant son tenant, lève HTTP 404 sinon."""
    result = await db.execute(
        select(Agent)
        .options(joinedload(Agent.role))
        .where(Agent.id == agent_id, Agent.tenant_id == tenant_id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent introuvable"
        )
    return agent
