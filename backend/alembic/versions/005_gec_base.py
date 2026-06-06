"""005 — GEC base (PRD-06A) : courriers, corbeilles, actions.

Revision ID: 005_gec_base
Revises: 004_unicite_libelles_archivage
Create Date: 2026-06-06

Contient :
- ENUM `sens_courrier` (entrant / sortant / interne)
- Référentiel `statuts_courrier` (seed des 4 statuts couverts en 06A,
  les autres seront ajoutés en migration 006 avec PRD-06B)
- Référentiel `actions_courrier` (seed des actions de PRD-06A)
- Tables : courriers, copies_courriers, imputations, notes_courrier,
  historiques_courrier, documents_courrier

Différé à PRD-06B (migration 006) :
- demandes_validation
- redirections
- alertes_envoyees
- etats_avancement
- 4 statuts complémentaires (a_valider, a_faire_valider, en_validation, valide)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "005_gec_base"
down_revision: Union[str, None] = "004_unicite_libelles_archivage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENUM sens_courrier sera créé automatiquement par sa.Enum() dans la
    # colonne `sens` de la table courriers. On le drop d'abord s'il existe
    # (cas de retraits/reprise de migration en dev).
    op.execute("DROP TYPE IF EXISTS sens_courrier")

    # ------------------------------------------------------------------------
    # statuts_courrier : référentiel statique
    # ------------------------------------------------------------------------
    op.create_table(
        "statuts_courrier",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("libelle", sa.String(64), nullable=False),
    )
    op.bulk_insert(
        sa.table(
            "statuts_courrier",
            sa.column("id", sa.SmallInteger),
            sa.column("code", sa.String),
            sa.column("libelle", sa.String),
        ),
        # PRD-06A : 2 statuts. PRD-06B ajoutera : a_valider (3), valide (4),
        # a_faire_valider (5), en_validation (6), rejete (7), cloture (8).
        [
            {"id": 1, "code": "a_traiter", "libelle": "À traiter"},
            {"id": 2, "code": "traite", "libelle": "Traité"},
        ],
    )

    # ------------------------------------------------------------------------
    # actions_courrier : référentiel statique
    # ------------------------------------------------------------------------
    op.create_table(
        "actions_courrier",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("libelle", sa.String(64), nullable=False),
    )
    op.bulk_insert(
        sa.table(
            "actions_courrier",
            sa.column("id", sa.SmallInteger),
            sa.column("code", sa.String),
            sa.column("libelle", sa.String),
        ),
        [
            {"id": 1, "code": "creation", "libelle": "Création du courrier"},
            {"id": 2, "code": "copie", "libelle": "Mise en copie"},
            {"id": 3, "code": "imputation", "libelle": "Imputation"},
            {"id": 4, "code": "reponse", "libelle": "Réponse créée"},
            {"id": 5, "code": "envoi", "libelle": "Envoi / clôture"},
            {"id": 6, "code": "note", "libelle": "Note ajoutée"},
            {"id": 7, "code": "ajout_document", "libelle": "Document ajouté"},
        ],
    )

    # ------------------------------------------------------------------------
    # courriers
    # ------------------------------------------------------------------------
    op.create_table(
        "courriers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Format YYYY-NNNNNN, séquence par année et par tenant
        sa.Column("numero_enregistrement", sa.String(16), nullable=False),
        sa.Column(
            "sens",
            sa.Enum("entrant", "sortant", "interne", name="sens_courrier"),
            nullable=False,
        ),
        sa.Column("ref_externe", sa.String(128)),
        sa.Column(
            "categorie_id",
            sa.BigInteger(),
            sa.ForeignKey("categories.id", ondelete="RESTRICT"),
        ),
        sa.Column("objet", sa.Text(), nullable=False),
        sa.Column("mots_cles", sa.Text()),
        sa.Column("observations", sa.Text()),
        # Dates
        sa.Column("date_courrier", sa.Date()),
        sa.Column("date_arrivee", sa.Date()),
        sa.Column("date_limite", sa.Date()),
        # Correspondant (entrant / sortant uniquement — nullable pour interne)
        sa.Column(
            "correspondant_id",
            sa.BigInteger(),
            sa.ForeignKey("correspondants.id", ondelete="RESTRICT"),
        ),
        # Destinataire interne (toujours rempli)
        sa.Column(
            "departement_destinataire_id",
            sa.BigInteger(),
            sa.ForeignKey("departements.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "agent_destinataire_id",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Pièce principale OBLIGATOIRE (décision PRD-06A)
        sa.Column(
            "document_principal_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Workflow
        sa.Column(
            "statut_id",
            sa.SmallInteger(),
            sa.ForeignKey("statuts_courrier.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "agent_proprietaire_id",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Chaînage réponse → courrier d'origine
        sa.Column(
            "courrier_origine_id",
            sa.BigInteger(),
            sa.ForeignKey("courriers.id", ondelete="SET NULL"),
        ),
        # Audit
        sa.Column("supprime", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_by",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "numero_enregistrement",
            name="uq_courriers_tenant_numero",
        ),
        # Cohérence métier : un courrier entrant ou sortant DOIT avoir un correspondant
        sa.CheckConstraint(
            "(sens = 'interne') OR (correspondant_id IS NOT NULL)",
            name="ck_courriers_correspondant_si_externe",
        ),
    )
    op.create_index(
        "idx_courriers_proprio",
        "courriers",
        ["tenant_id", "agent_proprietaire_id", "statut_id"],
        postgresql_where=sa.text("NOT supprime"),
    )
    op.create_index(
        "idx_courriers_date_limite",
        "courriers",
        ["tenant_id", "date_limite"],
        postgresql_where=sa.text("date_limite IS NOT NULL AND NOT supprime"),
    )
    op.create_index(
        "idx_courriers_origine",
        "courriers",
        ["courrier_origine_id"],
        postgresql_where=sa.text("courrier_origine_id IS NOT NULL"),
    )

    # ------------------------------------------------------------------------
    # copies_courriers
    # ------------------------------------------------------------------------
    op.create_table(
        "copies_courriers",
        sa.Column(
            "courrier_id",
            sa.BigInteger(),
            sa.ForeignKey("courriers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "agent_id",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("lu", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "ajoute_par",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "ajoute_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_copies_agent", "copies_courriers", ["agent_id"])

    # ------------------------------------------------------------------------
    # imputations (historique des transferts de propriété)
    # ------------------------------------------------------------------------
    op.create_table(
        "imputations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "courrier_id",
            sa.BigInteger(),
            sa.ForeignKey("courriers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_imputeur_id",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "agent_impute_id",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("instruction", sa.Text()),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_imputations_courrier", "imputations", ["courrier_id", sa.text("ts DESC")]
    )

    # ------------------------------------------------------------------------
    # notes_courrier (post-it)
    # ------------------------------------------------------------------------
    op.create_table(
        "notes_courrier",
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
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
        ),
        sa.Column("contenu", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_notes_courrier", "notes_courrier", ["courrier_id", sa.text("created_at DESC")]
    )

    # ------------------------------------------------------------------------
    # historiques_courrier (timeline visible par l'utilisateur)
    # ------------------------------------------------------------------------
    op.create_table(
        "historiques_courrier",
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
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "action_id",
            sa.SmallInteger(),
            sa.ForeignKey("actions_courrier.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("payload", JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_histo_courrier",
        "historiques_courrier",
        ["courrier_id", sa.text("ts DESC")],
    )

    # ------------------------------------------------------------------------
    # documents_courrier (pièces additionnelles, M:N)
    # ------------------------------------------------------------------------
    op.create_table(
        "documents_courrier",
        sa.Column(
            "courrier_id",
            sa.BigInteger(),
            sa.ForeignKey("courriers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "document_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "ajoute_par",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "ajoute_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("documents_courrier")
    op.drop_table("historiques_courrier")
    op.drop_table("notes_courrier")
    op.drop_table("imputations")
    op.drop_table("copies_courriers")
    op.drop_table("courriers")
    op.drop_table("actions_courrier")
    op.drop_table("statuts_courrier")
    op.execute("DROP TYPE IF EXISTS sens_courrier")
