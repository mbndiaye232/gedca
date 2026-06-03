"""Dépendances FastAPI partagées : session DB, agent courant, vérifications RBAC."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import get_db
from app.models import Agent
from app.services.jwt import JetonInvalideError, decoder_jeton

# Le token est lu depuis l'en-tête Authorization: Bearer <token>.
# tokenUrl est purement informatif pour /docs ; pas de flow OAuth réel.
_oauth2_schema = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


SessionDB = Annotated[AsyncSession, Depends(get_db)]


async def agent_courant(
    token: Annotated[str | None, Depends(_oauth2_schema)],
    db: SessionDB,
) -> Agent:
    """Décode le JWT, charge l'agent en base, vérifie qu'il est actif.

    Lève HTTP 401 si le token est absent, invalide ou que l'agent est désactivé.
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        jeton = decoder_jeton(token)
    except JetonInvalideError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalide : {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    result = await db.execute(
        select(Agent)
        .options(joinedload(Agent.role))
        .where(Agent.id == jeton.agent_id, Agent.tenant_id == jeton.tenant_id)
    )
    agent = result.scalar_one_or_none()
    if agent is None or not agent.actif:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return agent


AgentCourant = Annotated[Agent, Depends(agent_courant)]


def _verifier_role(agent: Agent, roles_autorises: set[str]) -> None:
    """Vérifie que l'agent a un rôle autorisé, sinon lève HTTP 403."""
    if agent.role.code not in roles_autorises:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé pour ce rôle",
        )


async def agent_superviseur(agent: AgentCourant) -> Agent:
    """Dépendance : exige le rôle superviseur."""
    _verifier_role(agent, {"superviseur"})
    return agent


async def agent_archiviste_ou_plus(agent: AgentCourant) -> Agent:
    """Dépendance : exige archiviste ou superviseur."""
    _verifier_role(agent, {"superviseur", "archiviste"})
    return agent


AgentSuperviseur = Annotated[Agent, Depends(agent_superviseur)]
AgentArchivisteOuPlus = Annotated[Agent, Depends(agent_archiviste_ou_plus)]


def ip_requete(request: Request) -> str | None:
    """Extrait l'IP du client en respectant X-Forwarded-For si présent."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Première IP de la liste = client originel
        return forwarded.split(",")[0].strip()
    if request.client is None:
        return None
    return request.client.host


IpClient = Annotated[str | None, Depends(ip_requete)]
