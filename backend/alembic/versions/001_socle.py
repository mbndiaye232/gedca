"""001 — Socle (PRD-01) : extensions, FTS française, tenants, agents, audit_log.

Revision ID: 001_socle
Revises:
Create Date: 2026-05-31

Contient :
- Extensions PostgreSQL (`pgcrypto`, `pg_trgm`, `unaccent`, `vector`)
- Configuration FTS française avec unaccent (`french_unaccent`)
- Référentiels statiques : `roles`, `types_correspondant`
- `tenants`
- `departements`, `agents`
- `audit_log`
- Seed initial : rôles, types correspondant, tenant de test, agent superviseur

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import BYTEA, INET, JSONB

revision: str = "001_socle"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------------
    # Extensions PostgreSQL
    # ------------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Configuration de recherche plein texte française sans accents
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_ts_config WHERE cfgname = 'french_unaccent'
            ) THEN
                CREATE TEXT SEARCH CONFIGURATION french_unaccent (COPY = french);
                ALTER TEXT SEARCH CONFIGURATION french_unaccent
                    ALTER MAPPING FOR hword, hword_part, word
                    WITH unaccent, french_stem;
            END IF;
        END
        $$;
        """
    )

    # ------------------------------------------------------------------------
    # Référentiels statiques
    # ------------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("libelle", sa.String(64), nullable=False),
    )

    op.create_table(
        "types_correspondant",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("libelle", sa.String(64), nullable=False),
    )

    # ------------------------------------------------------------------------
    # tenants
    # ------------------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("raison_sociale", sa.String(255), nullable=False),
        sa.Column("adresse", sa.Text()),
        sa.Column("telephone", sa.String(64)),
        sa.Column("email", sa.String(255)),
        sa.Column("logo_chemin", sa.Text()),
        sa.Column("smtp_host", sa.String(255)),
        sa.Column("smtp_port", sa.Integer()),
        sa.Column("smtp_user", sa.String(255)),
        sa.Column("smtp_password_enc", BYTEA()),
        sa.Column("smtp_from", sa.String(255)),
        sa.Column("smtp_use_tls", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ai_provider", sa.String(32), nullable=False, server_default="anthropic"),
        sa.Column("ai_config", JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "delai_alerte_jours", sa.Integer(), nullable=False, server_default="4"
        ),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ------------------------------------------------------------------------
    # departements
    # ------------------------------------------------------------------------
    op.create_table(
        "departements",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.String(32)),
        sa.Column("libelle", sa.String(255), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("tenant_id", "libelle", name="uq_departements_tenant_libelle"),
    )

    # ------------------------------------------------------------------------
    # agents
    # ------------------------------------------------------------------------
    op.create_table(
        "agents",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("login", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255)),
        sa.Column(
            "auth_provider",
            sa.String(16),
            nullable=False,
            server_default="local",
        ),
        sa.Column("nom", sa.String(128), nullable=False),
        sa.Column("prenom", sa.String(128), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("telephone", sa.String(64)),
        sa.Column("photo_chemin", sa.String(512)),
        sa.Column("fonction", sa.String(128)),
        sa.Column(
            "departement_id",
            sa.BigInteger(),
            sa.ForeignKey("departements.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "role_id",
            sa.SmallInteger(),
            sa.ForeignKey("roles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("derniere_connexion", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("tenant_id", "login", name="uq_agents_tenant_login"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_agents_tenant_email"),
        sa.CheckConstraint(
            "auth_provider IN ('local', 'ldap')", name="ck_agents_auth_provider"
        ),
        sa.CheckConstraint(
            "auth_provider = 'ldap' OR password_hash IS NOT NULL",
            name="ck_agents_local_has_password",
        ),
    )
    op.create_index(
        "idx_agents_tenant_actif",
        "agents",
        ["tenant_id", "actif"],
    )
    op.create_index(
        "idx_agents_departement",
        "agents",
        ["departement_id"],
        postgresql_where=sa.text("actif"),
    )

    # ------------------------------------------------------------------------
    # audit_log
    # ------------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entite", sa.String(64)),
        sa.Column("entite_id", sa.BigInteger()),
        sa.Column("payload", JSONB(), nullable=False, server_default="{}"),
        sa.Column("ip", INET()),
        sa.Column("user_agent", sa.Text()),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_audit_tenant_ts", "audit_log", ["tenant_id", sa.text("ts DESC")])
    op.create_index("idx_audit_entite", "audit_log", ["entite", "entite_id"])
    op.create_index("idx_audit_agent", "audit_log", ["agent_id"])

    # ------------------------------------------------------------------------
    # Seed minimal — référentiels statiques uniquement.
    # Le seed du tenant de test et de l'agent superviseur initial est dans
    # backend/scripts/seed_dev.py (exécuté manuellement en dev).
    # ------------------------------------------------------------------------
    op.bulk_insert(
        sa.table(
            "roles",
            sa.column("id", sa.SmallInteger),
            sa.column("code", sa.String),
            sa.column("libelle", sa.String),
        ),
        [
            {"id": 1, "code": "superviseur", "libelle": "Superviseur"},
            {"id": 2, "code": "archiviste", "libelle": "Archiviste"},
            {"id": 3, "code": "agent_standard", "libelle": "Agent"},
        ],
    )
    op.bulk_insert(
        sa.table(
            "types_correspondant",
            sa.column("id", sa.SmallInteger),
            sa.column("code", sa.String),
            sa.column("libelle", sa.String),
        ),
        [
            {"id": 1, "code": "personne_morale", "libelle": "Personne morale"},
            {"id": 2, "code": "personne_physique", "libelle": "Personne physique"},
        ],
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("agents")
    op.drop_table("departements")
    op.drop_table("tenants")
    op.drop_table("types_correspondant")
    op.drop_table("roles")
    # Configuration FTS et extensions volontairement conservées
    # (idempotent — utilisable par d'autres bases sur le même cluster).
