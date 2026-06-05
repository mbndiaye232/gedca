"""002 — Compléments PRD-01 : ajout de `cellulaire` et `adresse` sur `agents`.

Revision ID: 002_complements_prd01
Revises: 001_socle
Create Date: 2026-06-05

Aligne le modèle `agents` avec la base d'origine (`docs/dumpbdsoftged.txt`) qui
distingue téléphone fixe (`tel`) et cellulaire (`cel`), et stocke aussi une
adresse postale (`adr`). Cf. `docs/reconciliation-bdsoftged.md`.

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_complements_prd01"
down_revision: Union[str, None] = "001_socle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("cellulaire", sa.String(64), nullable=True))
    op.add_column("agents", sa.Column("adresse", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "adresse")
    op.drop_column("agents", "cellulaire")
