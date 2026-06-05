"""Schémas Pydantic pour catégories, thématiques, types de document."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CategorieLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    libelle: str
    description: str | None
    actif: bool


class CategorieCreation(BaseModel):
    libelle: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(None, max_length=512)


class ReferentielLecture(BaseModel):
    """Sortie commune pour thématiques et types."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    libelle: str
    actif: bool


class ReferentielCreation(BaseModel):
    libelle: str = Field(..., min_length=1, max_length=128)
