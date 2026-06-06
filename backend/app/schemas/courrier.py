"""Schémas Pydantic du module GEC (PRD-06A)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SensCourrier = Literal["entrant", "sortant", "interne"]

# Codes des 8 corbeilles (PRD-06A §5.2)
CorbeilleCode = Literal[
    "a_traiter",
    "traite",
    "en_copie",
    "en_retard",
    "a_valider",
    "valides",
    "a_faire_valider",
    "en_validation",
]


# ============================================================================
# Création / mise à jour
# ============================================================================


class CourrierCreation(BaseModel):
    """Body de POST /api/courriers (JSON dans une partie multipart).

    La pièce principale arrive en tant que fichier multipart `fichier` séparé.
    """

    sens: SensCourrier
    ref_externe: str | None = Field(None, max_length=128)
    categorie_id: int | None = None
    objet: str = Field(..., min_length=1)
    mots_cles: str | None = None
    observations: str | None = None

    date_courrier: date | None = None
    date_arrivee: date | None = None
    date_limite: date | None = None

    # Pour entrant / sortant : correspondant obligatoire (validé côté route)
    correspondant_id: int | None = None

    # Destinataire interne — `agent_destinataire_id` obligatoire
    departement_destinataire_id: int | None = None
    agent_destinataire_id: int

    # Titre + catégorie de la pièce principale (pour créer le Document)
    document_titre: str = Field(..., min_length=1, max_length=512)
    document_categorie_id: int


class CourrierMiseAJour(BaseModel):
    """PUT /api/courriers/{id} — modifications limitées en 06A."""

    ref_externe: str | None = Field(None, max_length=128)
    categorie_id: int | None = None
    objet: str | None = Field(None, min_length=1)
    mots_cles: str | None = None
    observations: str | None = None
    date_limite: date | None = None


# ============================================================================
# Actions sur un courrier
# ============================================================================


class CopieBody(BaseModel):
    """Body de POST /api/courriers/{id}/copies."""

    agent_ids: list[int] = Field(..., min_length=1)


class ImputerBody(BaseModel):
    """Body de POST /api/courriers/{id}/imputer."""

    agent_impute_id: int
    instruction: str | None = None


class RepondreBody(BaseModel):
    """Body de POST /api/courriers/{id}/repondre.

    Crée un nouveau courrier sortant lié au courrier d'origine.
    """

    objet: str = Field(..., min_length=1)
    mots_cles: str | None = None
    observations: str | None = None
    date_limite: date | None = None
    correspondant_id: int | None = None  # défaut : reprendre celui de l'origine
    agent_destinataire_id: int  # qui porte la réponse
    departement_destinataire_id: int | None = None
    document_titre: str = Field(..., min_length=1, max_length=512)
    document_categorie_id: int


class NoteCreation(BaseModel):
    contenu: str = Field(..., min_length=1, max_length=1000)


# ============================================================================
# Lecture
# ============================================================================


class StatutCourrierLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    libelle: str


class ActionCourrierLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    libelle: str


class AgentResume(BaseModel):
    """Résumé d'agent pour affichage rapide (pas d'infos sensibles)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    email: str | None


class CorrespondantResume(BaseModel):
    """Résumé d'un correspondant pour la liste des courriers."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    raison_sociale: str | None
    nom: str | None
    prenom: str | None


class CourrierLecture(BaseModel):
    """Lecture courte d'un courrier (utilisée dans les listes de corbeille)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_enregistrement: str
    sens: SensCourrier
    ref_externe: str | None
    categorie_id: int | None
    objet: str
    mots_cles: str | None
    observations: str | None
    date_courrier: date | None
    date_arrivee: date | None
    date_limite: date | None
    correspondant_id: int | None
    correspondant: CorrespondantResume | None = None
    agent_destinataire_id: int
    agent_proprietaire_id: int
    departement_destinataire_id: int | None
    document_principal_id: int
    statut: StatutCourrierLecture
    courrier_origine_id: int | None
    created_at: datetime
    created_by: int | None
    updated_at: datetime


class NoteLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    agent_id: int | None
    contenu: str
    created_at: datetime


class HistoriqueLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    agent_id: int | None
    action: ActionCourrierLecture
    payload: dict[str, Any]
    ts: datetime


class CourrierDetail(CourrierLecture):
    """Lecture étendue avec pièces, copies, notes, historique."""

    copies: list[AgentResume] = []
    notes: list[NoteLecture] = []
    historique: list[HistoriqueLecture] = []
    pieces_additionnelles: list[int] = []  # document_ids


# ============================================================================
# Corbeilles
# ============================================================================


class CompteurCorbeille(BaseModel):
    """Une carte de corbeille avec son compteur."""

    code: CorbeilleCode
    libelle: str
    compteur: int
    actif_en_06a: bool = True  # False pour les 4 corbeilles différées en 06B


class CompteursCorbeilles(BaseModel):
    """Réponse de GET /api/courriers/corbeilles/compteurs."""

    corbeilles: list[CompteurCorbeille]
