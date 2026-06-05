"""Schémas Pydantic pour l'archivage physique (6 niveaux)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ----- Schémas de lecture (sortie API) -------------------------------------


class _EmplacementBase(BaseModel):
    """Champs communs à tous les niveaux."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: int
    libelle: str


class SiteLecture(_EmplacementBase):
    description: str | None


class LocalLecture(_EmplacementBase):
    site_id: int
    description: str | None


class RayonLecture(_EmplacementBase):
    local_id: int


class BoiteLecture(_EmplacementBase):
    rayon_id: int


class DossierLecture(_EmplacementBase):
    boite_id: int


class SousDossierLecture(_EmplacementBase):
    dossier_id: int


# ----- Schémas de création --------------------------------------------------


class SiteCreation(BaseModel):
    libelle: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class LocalCreation(BaseModel):
    site_id: int
    libelle: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class RayonCreation(BaseModel):
    local_id: int
    libelle: str = Field(..., min_length=1, max_length=255)


class BoiteCreation(BaseModel):
    rayon_id: int
    libelle: str = Field(..., min_length=1, max_length=255)


class DossierCreation(BaseModel):
    boite_id: int
    libelle: str = Field(..., min_length=1, max_length=255)


class SousDossierCreation(BaseModel):
    dossier_id: int
    libelle: str = Field(..., min_length=1, max_length=255)


# ----- Schémas de mise à jour (libelle / description uniquement) -----------


class EmplacementMiseAJour(BaseModel):
    libelle: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


# ----- Schéma du code complet et détail des libellés ----------------------


class NiveauResume(BaseModel):
    """Résumé d'un niveau (numéro + libellé) pour l'affichage du chemin."""

    numero: int
    libelle: str


class CodeComplet(BaseModel):
    """Réponse de GET /api/archivage/sous-dossiers/{id}/code."""

    sous_dossier_id: int
    code_complet: str  # ex: "05.02.01.001.04.07"
    site: NiveauResume
    local: NiveauResume
    rayon: NiveauResume
    boite: NiveauResume
    dossier: NiveauResume
    sous_dossier: NiveauResume
