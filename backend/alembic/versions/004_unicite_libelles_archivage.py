"""004 — Unicité du libellé par parent sur les 6 niveaux d'archivage physique.

Revision ID: 004_unicite_libelles_archivage
Revises: 003_stockage_archivage
Create Date: 2026-06-06

Empêche deux frères/sœurs d'avoir le même libellé au sein du même parent :
- 2 sites du même tenant
- 2 locaux du même site
- 2 rayons du même local
- 2 boîtes du même rayon
- 2 dossiers de la même boîte
- 2 sous-dossiers du même dossier

Reste autorisé : un local « R+1 » dans le site A et un local « R+1 » dans le
site B (les parents sont différents).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "004_unicite_libelles_archivage"
down_revision: Union[str, None] = "003_stockage_archivage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_sites_tenant_libelle", "sites", ["tenant_id", "libelle"]
    )
    op.create_unique_constraint(
        "uq_locaux_site_libelle", "locaux_salles", ["site_id", "libelle"]
    )
    op.create_unique_constraint(
        "uq_rayons_local_libelle", "rayons", ["local_id", "libelle"]
    )
    op.create_unique_constraint(
        "uq_boites_rayon_libelle", "boites", ["rayon_id", "libelle"]
    )
    op.create_unique_constraint(
        "uq_dossiers_boite_libelle", "dossiers_classeurs", ["boite_id", "libelle"]
    )
    op.create_unique_constraint(
        "uq_sous_dossiers_dossier_libelle",
        "sous_dossiers",
        ["dossier_id", "libelle"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_sous_dossiers_dossier_libelle", "sous_dossiers", type_="unique")
    op.drop_constraint("uq_dossiers_boite_libelle", "dossiers_classeurs", type_="unique")
    op.drop_constraint("uq_boites_rayon_libelle", "boites", type_="unique")
    op.drop_constraint("uq_rayons_local_libelle", "rayons", type_="unique")
    op.drop_constraint("uq_locaux_site_libelle", "locaux_salles", type_="unique")
    op.drop_constraint("uq_sites_tenant_libelle", "sites", type_="unique")
