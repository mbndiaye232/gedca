"""008 — Réinitialisation de mot de passe par email.

Revision ID: 008_reset_mdp
Revises: 007_redirection_et_alertes
Create Date: 2026-06-09

Table `tokens_reset_mdp` pour le workflow :
1. Un superviseur déclenche la réinitialisation du mot de passe d'un agent
2. Le système génère un token aléatoire (`secrets.token_urlsafe(32)`)
   et stocke son **hash SHA-256** (jamais le token brut)
3. Un email est envoyé à l'agent avec le lien `/reset-mdp?token=...`
4. L'agent ouvre le lien, saisit son nouveau mot de passe, le backend
   valide le token (hash + non expiré + non utilisé) et change le mdp
5. Le token est marqué `utilise_at`, ne peut plus servir

Durée de validité : 24h (paramétré côté service, pas dans le schéma).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_reset_mdp"
down_revision: Union[str, None] = "007_redirection_et_alertes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tokens_reset_mdp",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "agent_id",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Hash SHA-256 (hex) du token aléatoire — 64 caractères.
        # Le token brut n'est PAS stocké, comme pour un mot de passe.
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "cree_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("expire_at", sa.DateTime(timezone=True), nullable=False),
        # NULL tant que le token n'a pas été utilisé.
        sa.Column("utilise_at", sa.DateTime(timezone=True)),
        sa.Column(
            "demande_par",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
        ),
    )
    # Index pour invalider les anciens tokens d'un agent quand on en
    # génère un nouveau (best practice : un seul token actif à la fois).
    op.create_index(
        "idx_tokens_reset_agent_actifs",
        "tokens_reset_mdp",
        ["agent_id"],
        postgresql_where=sa.text("utilise_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_tokens_reset_agent_actifs", table_name="tokens_reset_mdp")
    op.drop_table("tokens_reset_mdp")
