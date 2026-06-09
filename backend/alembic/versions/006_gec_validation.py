"""006 — GEC validation (PRD-06B) : workflow demander/valider une réponse.

Revision ID: 006_gec_validation
Revises: 005_gec_base
Create Date: 2026-06-09

Implémente le workflow de validation décrit dans le PDF Corbeilles (p. 4-7) :

    [a_faire_valider] → demander_validation → [en_validation]
                                                    ↓ valider
                                              [valide] → envoyer → [traite]

Ajouts par rapport à 06A :
- 3 statuts complémentaires : `a_faire_valider` (3), `en_validation` (4),
  `valide` (5)
- 2 actions complémentaires : `demande_validation` (8), `validation` (9)
- Colonne `agent_valideur_id` sur `courriers` (qui doit / a validé)
- Index partiel pour optimiser la corbeille « À valider » (statut=4,
  agent_valideur_id=N)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_gec_validation"
down_revision: Union[str, None] = "005_gec_base"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --------------------------------------------------------------------
    # Statuts complémentaires
    # --------------------------------------------------------------------
    op.bulk_insert(
        sa.table(
            "statuts_courrier",
            sa.column("id", sa.SmallInteger),
            sa.column("code", sa.String),
            sa.column("libelle", sa.String),
        ),
        [
            {"id": 3, "code": "a_faire_valider", "libelle": "À faire valider"},
            {"id": 4, "code": "en_validation", "libelle": "En validation"},
            {"id": 5, "code": "valide", "libelle": "Validé"},
        ],
    )

    # --------------------------------------------------------------------
    # Actions complémentaires
    # --------------------------------------------------------------------
    op.bulk_insert(
        sa.table(
            "actions_courrier",
            sa.column("id", sa.SmallInteger),
            sa.column("code", sa.String),
            sa.column("libelle", sa.String),
        ),
        [
            {"id": 8, "code": "demande_validation", "libelle": "Demande de validation"},
            {"id": 9, "code": "validation", "libelle": "Validation accordée"},
        ],
    )

    # --------------------------------------------------------------------
    # courriers.agent_valideur_id
    # --------------------------------------------------------------------
    # NULL tant que la validation n'est pas demandée. Reste rempli après
    # validation pour tracer qui a validé (info historique également
    # journalisée dans historiques_courrier).
    op.add_column(
        "courriers",
        sa.Column(
            "agent_valideur_id",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )

    # Index partiel : sert la corbeille "À valider" (côté valideur) et
    # "En validation" (côté demandeur). Filtre supprimé évite de scanner
    # les courriers archivés.
    op.create_index(
        "idx_courriers_valideur",
        "courriers",
        ["tenant_id", "agent_valideur_id", "statut_id"],
        postgresql_where=sa.text(
            "agent_valideur_id IS NOT NULL AND NOT supprime"
        ),
    )


def downgrade() -> None:
    op.drop_index("idx_courriers_valideur", table_name="courriers")
    op.drop_column("courriers", "agent_valideur_id")

    # Supprime les seeds (les FKs depuis historiques_courrier.action_id et
    # courriers.statut_id en RESTRICT empêcheraient le downgrade si des
    # données réelles utilisent ces ids — c'est voulu, on échoue plutôt
    # que de corrompre).
    op.execute("DELETE FROM actions_courrier WHERE id IN (8, 9)")
    op.execute("DELETE FROM statuts_courrier WHERE id IN (3, 4, 5)")
