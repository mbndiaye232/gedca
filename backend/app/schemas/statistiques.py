"""Schémas Pydantic pour les statistiques d'activité par agent."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class StatistiquesActiviteAgent(BaseModel):
    """Une ligne de statistiques pour un agent sur une période."""

    model_config = ConfigDict(from_attributes=True)

    agent_id: int
    nom: str
    prenom: str
    departement: str | None = None
    fonction: str | None = None

    # Compteurs des actions effectuées PAR cet agent dans la période
    courriers_crees: int = 0           # action_id = 1
    mises_en_copie: int = 0            # action_id = 2 (qu'il a faites)
    imputations_emises: int = 0        # action_id = 3 (qu'il a imputées)
    reponses_creees: int = 0           # action_id = 4
    courriers_envoyes: int = 0         # action_id = 5
    notes_ajoutees: int = 0            # action_id = 6
    documents_ajoutes: int = 0         # action_id = 7
    validations_demandees: int = 0     # action_id = 8 (qu'il a demandées)
    validations_accordees: int = 0     # action_id = 9 (qu'il a accordées)

    # Compteurs des courriers où cet agent est DESTINATAIRE
    # (pas une action — c'est un état actuel à la fin de la période)
    courriers_a_traiter: int = 0       # courriers ouverts qui sont à lui
    courriers_en_retard: int = 0       # parmi ceux à traiter

    @property
    def total_actions(self) -> int:
        return (
            self.courriers_crees + self.mises_en_copie + self.imputations_emises
            + self.reponses_creees + self.courriers_envoyes + self.notes_ajoutees
            + self.documents_ajoutes + self.validations_demandees
            + self.validations_accordees
        )


class StatistiquesActiviteReponse(BaseModel):
    """Réponse de GET /api/statistiques/activite-agents."""

    date_debut: date
    date_fin: date
    agents: list[StatistiquesActiviteAgent]


class StatistiquesPeriode(BaseModel):
    """Body / Query pour préciser la période — les deux champs sont
    optionnels. Si `date_debut` est None, le backend utilise la date
    du premier courrier du tenant (début d'exploitation). Si `date_fin`
    est None, le backend utilise la date du jour."""

    date_debut: date | None = Field(
        None, description="Début de la période (incluse). Défaut : début d'exploitation."
    )
    date_fin: date | None = Field(
        None, description="Fin de la période (incluse). Défaut : aujourd'hui."
    )
