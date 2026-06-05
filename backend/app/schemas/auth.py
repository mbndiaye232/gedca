"""Schémas Pydantic pour l'authentification."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IdentifiantsConnexion(BaseModel):
    """Body de POST /api/auth/login."""

    login: str = Field(..., min_length=1, max_length=64)
    mot_de_passe: str = Field(..., min_length=1, max_length=255)


class AgentSession(BaseModel):
    """Représentation de l'agent connecté incluse dans la réponse de login."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    nom: str
    prenom: str
    email: str | None
    role: str  # code du rôle (superviseur, archiviste, agent_standard)
    tenant_id: int


class ReponseConnexion(BaseModel):
    """Body de POST /api/auth/login en sortie."""

    access_token: str
    token_type: str = "bearer"
    expire_at: datetime
    agent: AgentSession
