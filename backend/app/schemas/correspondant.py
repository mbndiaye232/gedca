"""Schémas Pydantic des correspondants."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

# IDs des types_correspondant seedés en migration 001
TYPE_MORALE = 1
TYPE_PHYSIQUE = 2


class CorrespondantLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type_id: int
    raison_sociale: str | None
    civilite: str | None
    nom: str | None
    prenom: str | None
    fonction: str | None
    adresse: str | None
    telephone: str | None
    email: str | None
    actif: bool


class CorrespondantCreation(BaseModel):
    type_id: int = Field(..., description="1=personne morale, 2=personne physique")
    raison_sociale: str | None = Field(None, max_length=255)
    civilite: str | None = Field(None, max_length=16)
    nom: str | None = Field(None, max_length=128)
    prenom: str | None = Field(None, max_length=128)
    fonction: str | None = Field(None, max_length=128)
    adresse: str | None = None
    telephone: str | None = Field(None, max_length=64)
    email: EmailStr | None = None

    @model_validator(mode="after")
    def coherence_identification(self) -> "CorrespondantCreation":
        if self.type_id == TYPE_MORALE and not self.raison_sociale:
            raise ValueError("Raison sociale obligatoire pour une personne morale")
        if self.type_id == TYPE_PHYSIQUE and not self.nom:
            raise ValueError("Nom obligatoire pour une personne physique")
        return self


class CorrespondantMiseAJour(BaseModel):
    raison_sociale: str | None = Field(None, max_length=255)
    civilite: str | None = Field(None, max_length=16)
    nom: str | None = Field(None, max_length=128)
    prenom: str | None = Field(None, max_length=128)
    fonction: str | None = Field(None, max_length=128)
    adresse: str | None = None
    telephone: str | None = Field(None, max_length=64)
    email: EmailStr | None = None
