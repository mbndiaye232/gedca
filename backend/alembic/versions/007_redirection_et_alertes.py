"""007 — Redirection + Alertes de retard.

Revision ID: 007_redirection_et_alertes
Revises: 006_gec_validation
Create Date: 2026-06-09

Deux fonctionnalités cousines :

1. **Redirection** (docs/redirection.pdf) — un agent en congés ou indisponible
   peut signaler son absence et rediriger tout nouveau courrier vers un
   collègue substitut. Règle : une seule redirection active à la fois par
   agent, contrainte exprimée par un index unique partiel.

2. **Alertes de retard** — job Celery beat quotidien qui notifie les
   destinataires d'un courrier à J-5, J-3, J-2, J-1 et J0 de la date
   limite. Anti-doublon via index unique sur (courrier_id, agent_id, palier).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_redirection_et_alertes"
down_revision: Union[str, None] = "006_gec_validation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --------------------------------------------------------------------
    # redirections
    # --------------------------------------------------------------------
    # On garde l'historique des redirections (active + supprimées) plutôt
    # que de supprimer physiquement à la fin — ça permet de retracer "à
    # tel moment du passé, quelle redirection était en cours".
    op.create_table(
        "redirections",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # L'agent absent / qui redirige son courrier
        sa.Column(
            "agent_redirige_id",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # L'agent substitut qui recevra les courriers à sa place
        sa.Column(
            "agent_substitut_id",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "cree_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "cree_par",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("supprime_at", sa.DateTime(timezone=True)),
        sa.Column(
            "supprime_par",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
        ),
        sa.CheckConstraint(
            "agent_redirige_id <> agent_substitut_id",
            name="ck_redirection_substitut_different",
        ),
    )
    # Une seule redirection ACTIVE par agent — la contrainte essentielle.
    # L'index partiel n'inclut PAS les lignes désactivées, donc on peut
    # avoir un historique illimité d'anciennes redirections pour un même
    # agent.
    op.create_index(
        "uq_redirections_active_par_agent",
        "redirections",
        ["tenant_id", "agent_redirige_id"],
        unique=True,
        postgresql_where=sa.text("active = TRUE"),
    )
    # Index secondaire pour résoudre rapidement « est-ce que je suis
    # substitut de quelqu'un ? » (utile pour les compteurs UI)
    op.create_index(
        "idx_redirections_substitut",
        "redirections",
        ["tenant_id", "agent_substitut_id"],
        postgresql_where=sa.text("active = TRUE"),
    )

    # --------------------------------------------------------------------
    # alertes_retard_envoyees
    # --------------------------------------------------------------------
    # Tracent les alertes émises pour éviter le double envoi quand le
    # cron tourne plusieurs fois la même journée (relance, debug…).
    # `palier` ∈ {5, 3, 2, 1, 0} — jours restants avant la date limite.
    op.create_table(
        "alertes_retard_envoyees",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "courrier_id",
            sa.BigInteger(),
            sa.ForeignKey("courriers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("palier", sa.SmallInteger(), nullable=False),
        sa.Column(
            "envoye_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "courrier_id",
            "agent_id",
            "palier",
            name="uq_alertes_retard_unique",
        ),
        sa.CheckConstraint(
            "palier IN (5, 3, 2, 1, 0)",
            name="ck_alertes_retard_palier_valide",
        ),
    )

    # --------------------------------------------------------------------
    # Nouvelle action_courrier 'redirection'
    # --------------------------------------------------------------------
    # Tracée dans l'historique du courrier quand un courrier a été
    # redirigé à la création/imputation. Le payload contient l'agent
    # original (celui qui aurait dû recevoir) et l'agent substitut.
    op.bulk_insert(
        sa.table(
            "actions_courrier",
            sa.column("id", sa.SmallInteger),
            sa.column("code", sa.String),
            sa.column("libelle", sa.String),
        ),
        [
            {"id": 10, "code": "redirection", "libelle": "Redirection appliquée"},
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM actions_courrier WHERE id = 10")
    op.drop_table("alertes_retard_envoyees")
    op.drop_index("idx_redirections_substitut", table_name="redirections")
    op.drop_index("uq_redirections_active_par_agent", table_name="redirections")
    op.drop_table("redirections")
