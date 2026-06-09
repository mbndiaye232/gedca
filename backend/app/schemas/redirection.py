"""Schémas Pydantic pour la redirection."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RedirectionCreation(BaseModel):
    """Body de POST /api/redirections — l'agent connecté redirige son
    courrier vers `agent_substitut_id`."""

    agent_substitut_id: int = Field(
        ..., description="Agent qui recevra mes courriers pendant mon absence"
    )


class AgentMini(BaseModel):
    """Mini-profil agent pour l'affichage d'une redirection."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    email: str | None = None
    fonction: str | None = None


class RedirectionLecture(BaseModel):
    """Sortie standard d'une redirection."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_redirige_id: int
    agent_substitut_id: int
    cree_at: datetime
    cree_par: int | None
    active: bool
    supprime_at: datetime | None
    supprime_par: int | None


class RedirectionDetail(RedirectionLecture):
    """Lecture enrichie avec les mini-profils des agents impliqués."""

    agent_redirige: AgentMini | None = None
    agent_substitut: AgentMini | None = None
