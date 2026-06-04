"""Schémas Pydantic pour la structure (tenants côté UI superviseur)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StructureLecture(BaseModel):
    """Sortie de GET /api/structure."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    raison_sociale: str
    adresse: str | None
    telephone: str | None
    email: str | None
    logo_chemin: str | None


class StructureMiseAJour(BaseModel):
    """Body de PUT /api/structure (superviseur)."""

    raison_sociale: str | None = Field(None, min_length=1, max_length=255)
    adresse: str | None = None
    telephone: str | None = Field(None, max_length=64)
    email: EmailStr | None = None
    logo_chemin: str | None = Field(None, max_length=512)
