"""Schémas Pydantic pour les départements."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DepartementLecture(BaseModel):
    """Sortie standard d'un département."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str | None
    libelle: str
    actif: bool
    created_at: datetime


class DepartementCreation(BaseModel):
    code: str | None = Field(None, max_length=32)
    libelle: str = Field(..., min_length=1, max_length=255)


class DepartementMiseAJour(BaseModel):
    code: str | None = Field(None, max_length=32)
    libelle: str | None = Field(None, min_length=1, max_length=255)
