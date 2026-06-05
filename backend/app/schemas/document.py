"""Schémas Pydantic pour les documents."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentLecture(BaseModel):
    """Sortie standard d'un document (métadonnées, sans le contenu binaire)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    titre: str
    description: str | None
    resume: str | None
    mots_cles: str | None
    categorie_id: int | None
    thematique_id: int | None
    type_document_id: int | None
    mime: str
    taille_octets: int
    checksum_sha256: str
    date_document: date | None
    date_numerisation: datetime | None
    confidentiel: bool
    origine: str
    statut: str
    metadata_: dict[str, Any] = Field(alias="metadata")
    created_at: datetime
    created_by: int | None
    updated_at: datetime


class DocumentMetadonnees(BaseModel):
    """Body d'un upload — métadonnées (le fichier est en multipart)."""

    titre: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    resume: str | None = None
    mots_cles: str | None = None
    categorie_id: int
    thematique_id: int | None = None
    type_document_id: int | None = None
    date_document: date | None = None
    confidentiel: bool = False
    sous_dossier_id: int | None = None


class DocumentMiseAJour(BaseModel):
    """Body de PUT /api/documents/{id} (modification métadonnées)."""

    titre: str | None = Field(None, min_length=1, max_length=512)
    description: str | None = None
    resume: str | None = None
    mots_cles: str | None = None
    categorie_id: int | None = None
    thematique_id: int | None = None
    type_document_id: int | None = None
    date_document: date | None = None
    confidentiel: bool | None = None


class DocumentVersionLecture(BaseModel):
    """Sortie d'une version archivée."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    num_version: int
    checksum_sha256: str
    taille_octets: int
    commentaire: str | None
    created_at: datetime
    created_by: int | None


class DoublonReponse(BaseModel):
    """Renvoyé en HTTP 409 quand un upload est dédupliqué."""

    detail: str
    document_id: int
