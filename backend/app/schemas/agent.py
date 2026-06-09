"""Schémas Pydantic pour les agents."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AgentLecture(BaseModel):
    """Sortie standard d'un agent."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    nom: str
    prenom: str
    email: str | None
    telephone: str | None
    cellulaire: str | None
    adresse: str | None
    fonction: str | None
    photo_chemin: str | None
    departement_id: int | None
    role_id: int
    actif: bool
    derniere_connexion: datetime | None
    created_at: datetime


class AgentDestinataireLecture(BaseModel):
    """Vue restreinte d'un agent — utilisée par les sélecteurs (imputation,
    mise en copie, choix d'un destinataire de courrier).

    Pas d'infos sensibles (mot de passe, dernière connexion, etc.).
    Accessible à tout agent connecté, contrairement à AgentLecture qui
    est réservée au superviseur.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    email: str | None
    fonction: str | None
    departement_id: int | None


class AgentCreation(BaseModel):
    """Body de POST /api/agents (superviseur)."""

    login: str = Field(..., min_length=1, max_length=64)
    mot_de_passe: str = Field(..., min_length=8, max_length=255)
    nom: str = Field(..., min_length=1, max_length=128)
    prenom: str = Field(..., min_length=1, max_length=128)
    email: EmailStr | None = None
    telephone: str | None = Field(None, max_length=64)
    cellulaire: str | None = Field(None, max_length=64)
    adresse: str | None = None
    fonction: str | None = Field(None, max_length=128)
    departement_id: int | None = None
    role_id: int


class AgentMiseAJour(BaseModel):
    """Body de PUT /api/agents/{id} (superviseur). Tous les champs optionnels."""

    nom: str | None = Field(None, min_length=1, max_length=128)
    prenom: str | None = Field(None, min_length=1, max_length=128)
    email: EmailStr | None = None
    telephone: str | None = Field(None, max_length=64)
    cellulaire: str | None = Field(None, max_length=64)
    adresse: str | None = None
    fonction: str | None = Field(None, max_length=128)
    departement_id: int | None = None
    role_id: int | None = None


class MonProfilMiseAJour(BaseModel):
    """Body de PUT /api/agents/me — l'agent modifie ses propres infos."""

    email: EmailStr | None = None
    telephone: str | None = Field(None, max_length=64)
    cellulaire: str | None = Field(None, max_length=64)
    adresse: str | None = None
    photo_chemin: str | None = Field(None, max_length=512)
    mot_de_passe_actuel: str | None = None
    nouveau_mot_de_passe: str | None = Field(None, min_length=8, max_length=255)
