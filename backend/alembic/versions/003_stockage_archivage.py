"""003 — Stockage chiffré et archivage physique (PRD-02).

Revision ID: 003_stockage_archivage
Revises: 002_complements_prd01
Create Date: 2026-06-05

Contient :
- Référentiels : `categories`, `thematiques`, `types_document`
- `correspondants` (alignement complet avec la base d'origine)
- `documents` + `document_versions` avec trigger FTS et colonne embedding (pgvector)
- 6 tables d'archivage physique (vides — peuplées au runtime par PRD-05)
- `documents_sous_dossiers` (lien GED ↔ archivage physique)
- Vue `v_sous_dossiers_code` (code dotté calculé à la volée)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, TSVECTOR

revision: str = "003_stockage_archivage"
down_revision: Union[str, None] = "002_complements_prd01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------------
    # Référentiels
    # ------------------------------------------------------------------------
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("libelle", sa.String(128), nullable=False),
        sa.Column("description", sa.String(512)),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tenant_id", "libelle", name="uq_categories_tenant_libelle"),
    )

    op.create_table(
        "thematiques",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("libelle", sa.String(128), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tenant_id", "libelle", name="uq_thematiques_tenant_libelle"),
    )

    op.create_table(
        "types_document",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("libelle", sa.String(128), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tenant_id", "libelle", name="uq_types_document_tenant_libelle"),
    )

    # ------------------------------------------------------------------------
    # correspondants
    # ------------------------------------------------------------------------
    op.create_table(
        "correspondants",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "type_id",
            sa.SmallInteger(),
            sa.ForeignKey("types_correspondant.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("raison_sociale", sa.String(255)),
        sa.Column("civilite", sa.String(16)),
        sa.Column("nom", sa.String(128)),
        sa.Column("prenom", sa.String(128)),
        sa.Column("societe", sa.String(255)),
        sa.Column("fonction", sa.String(128)),
        sa.Column("adresse", sa.Text()),
        sa.Column("telephone", sa.String(64)),
        sa.Column("cellulaire", sa.String(64)),
        sa.Column("fax", sa.String(64)),
        sa.Column("email", sa.String(255)),
        sa.Column("notes", sa.Text()),
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
        sa.CheckConstraint(
            "(type_id = 1 AND raison_sociale IS NOT NULL) OR "
            "(type_id = 2 AND nom IS NOT NULL)",
            name="ck_correspondants_identification",
        ),
    )
    op.create_index("idx_correspondants_tenant", "correspondants", ["tenant_id", "actif"])
    op.execute(
        """
        CREATE INDEX idx_correspondants_search ON correspondants USING gin (
          to_tsvector('french_unaccent',
            coalesce(raison_sociale,'') || ' ' ||
            coalesce(nom,'') || ' ' || coalesce(prenom,'') || ' ' ||
            coalesce(societe,'')
          )
        );
        """
    )

    # ------------------------------------------------------------------------
    # documents (cœur du référentiel)
    # ------------------------------------------------------------------------
    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("titre", sa.String(512), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("resume", sa.Text()),
        sa.Column("mots_cles", sa.Text()),
        sa.Column(
            "categorie_id",
            sa.BigInteger(),
            sa.ForeignKey("categories.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "thematique_id",
            sa.BigInteger(),
            sa.ForeignKey("thematiques.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "type_document_id",
            sa.BigInteger(),
            sa.ForeignKey("types_document.id", ondelete="RESTRICT"),
        ),
        sa.Column("mime", sa.String(128), nullable=False),
        sa.Column("taille_octets", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("chemin_stockage", sa.Text(), nullable=False),
        sa.Column("nonce", BYTEA(), nullable=False),
        sa.Column("date_document", sa.Date()),
        sa.Column("date_numerisation", sa.DateTime(timezone=True)),
        sa.Column("texte_ocr", sa.Text()),
        sa.Column("recherche_fts", TSVECTOR()),
        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
        sa.Column("confidentiel", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("origine", sa.String(32), nullable=False, server_default="upload"),
        sa.Column("statut", sa.String(32), nullable=False, server_default="pret"),
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
        sa.Column(
            "updated_by",
            sa.BigInteger(),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
        ),
        sa.UniqueConstraint("tenant_id", "checksum_sha256", name="uq_documents_tenant_checksum"),
    )

    # Colonne pgvector — ajoutée via SQL brut pour éviter la dépendance Python
    op.execute("ALTER TABLE documents ADD COLUMN embedding vector(1024)")

    # Index
    op.execute(
        "CREATE INDEX idx_documents_fts ON documents USING gin (recherche_fts);"
    )
    op.execute(
        "CREATE INDEX idx_documents_embedding ON documents "
        "USING hnsw (embedding vector_cosine_ops);"
    )
    op.create_index(
        "idx_documents_tenant",
        "documents",
        ["tenant_id"],
        postgresql_where=sa.text("NOT supprime"),
    )
    op.create_index("idx_documents_categorie", "documents", ["categorie_id"])
    op.create_index("idx_documents_date_doc", "documents", ["date_document"])
    op.execute("CREATE INDEX idx_documents_metadata ON documents USING gin (metadata);")

    # Trigger d'alimentation du tsvector (français + unaccent + stemming)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION documents_fts_trigger() RETURNS trigger AS $$
        BEGIN
          NEW.recherche_fts :=
            setweight(to_tsvector('french_unaccent', coalesce(NEW.titre,'')),    'A') ||
            setweight(to_tsvector('french_unaccent', coalesce(NEW.mots_cles,'')), 'B') ||
            setweight(to_tsvector('french_unaccent', coalesce(NEW.resume,'')),    'B') ||
            setweight(to_tsvector('french_unaccent', coalesce(NEW.texte_ocr,'')), 'C');
          RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_documents_fts
          BEFORE INSERT OR UPDATE OF titre, mots_cles, resume, texte_ocr
          ON documents
          FOR EACH ROW EXECUTE FUNCTION documents_fts_trigger();
        """
    )

    # ------------------------------------------------------------------------
    # document_versions
    # ------------------------------------------------------------------------
    op.create_table(
        "document_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("num_version", sa.BigInteger(), nullable=False),
        sa.Column("chemin_stockage", sa.Text(), nullable=False),
        sa.Column("nonce", BYTEA(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("taille_octets", sa.BigInteger(), nullable=False),
        sa.Column("commentaire", sa.Text()),
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
        sa.UniqueConstraint("document_id", "num_version", name="uq_document_versions_doc_num"),
    )

    # ------------------------------------------------------------------------
    # Archivage physique — 6 niveaux (tables vides, peuplées en PRD-05)
    # ------------------------------------------------------------------------
    op.create_table(
        "sites",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("numero", sa.SmallInteger(), nullable=False),
        sa.Column("libelle", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.UniqueConstraint("tenant_id", "numero", name="uq_sites_tenant_numero"),
        sa.CheckConstraint("numero BETWEEN 1 AND 99", name="ck_sites_numero_range"),
    )

    op.create_table(
        "locaux_salles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "site_id",
            sa.BigInteger(),
            sa.ForeignKey("sites.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("numero", sa.SmallInteger(), nullable=False),
        sa.Column("libelle", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.UniqueConstraint("site_id", "numero", name="uq_locaux_site_numero"),
        sa.CheckConstraint("numero BETWEEN 1 AND 99", name="ck_locaux_numero_range"),
    )

    op.create_table(
        "rayons",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "local_id",
            sa.BigInteger(),
            sa.ForeignKey("locaux_salles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("numero", sa.SmallInteger(), nullable=False),
        sa.Column("libelle", sa.String(255), nullable=False),
        sa.UniqueConstraint("local_id", "numero", name="uq_rayons_local_numero"),
        sa.CheckConstraint("numero BETWEEN 1 AND 99", name="ck_rayons_numero_range"),
    )

    op.create_table(
        "boites",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "rayon_id",
            sa.BigInteger(),
            sa.ForeignKey("rayons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("numero", sa.SmallInteger(), nullable=False),
        sa.Column("libelle", sa.String(255), nullable=False),
        sa.UniqueConstraint("rayon_id", "numero", name="uq_boites_rayon_numero"),
        sa.CheckConstraint("numero BETWEEN 1 AND 999", name="ck_boites_numero_range"),
    )

    op.create_table(
        "dossiers_classeurs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "boite_id",
            sa.BigInteger(),
            sa.ForeignKey("boites.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("numero", sa.SmallInteger(), nullable=False),
        sa.Column("libelle", sa.String(255), nullable=False),
        sa.UniqueConstraint("boite_id", "numero", name="uq_dossiers_boite_numero"),
        sa.CheckConstraint("numero BETWEEN 1 AND 99", name="ck_dossiers_numero_range"),
    )

    op.create_table(
        "sous_dossiers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "dossier_id",
            sa.BigInteger(),
            sa.ForeignKey("dossiers_classeurs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("numero", sa.SmallInteger(), nullable=False),
        sa.Column("libelle", sa.String(255), nullable=False),
        sa.UniqueConstraint("dossier_id", "numero", name="uq_sous_dossiers_dossier_numero"),
        sa.CheckConstraint("numero BETWEEN 1 AND 99", name="ck_sous_dossiers_numero_range"),
    )

    op.create_table(
        "documents_sous_dossiers",
        sa.Column(
            "document_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "sous_dossier_id",
            sa.BigInteger(),
            sa.ForeignKey("sous_dossiers.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )

    # ------------------------------------------------------------------------
    # Vue dérivée du code dotté
    # ------------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE VIEW v_sous_dossiers_code AS
        SELECT
          sd.id AS sous_dossier_id,
          s.tenant_id,
          format('%02s.%02s.%02s.%03s.%02s.%02s',
            s.numero, l.numero, r.numero, b.numero, d.numero, sd.numero) AS code_complet,
          s.libelle  AS site,
          l.libelle  AS local,
          r.libelle  AS rayon,
          b.libelle  AS boite,
          d.libelle  AS dossier,
          sd.libelle AS sous_dossier
        FROM sous_dossiers sd
        JOIN dossiers_classeurs d ON d.id = sd.dossier_id
        JOIN boites b              ON b.id = d.boite_id
        JOIN rayons r              ON r.id = b.rayon_id
        JOIN locaux_salles l       ON l.id = r.local_id
        JOIN sites s               ON s.id = l.site_id;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_sous_dossiers_code")
    op.drop_table("documents_sous_dossiers")
    op.drop_table("sous_dossiers")
    op.drop_table("dossiers_classeurs")
    op.drop_table("boites")
    op.drop_table("rayons")
    op.drop_table("locaux_salles")
    op.drop_table("sites")
    op.drop_table("document_versions")
    op.execute("DROP TRIGGER IF EXISTS trg_documents_fts ON documents")
    op.execute("DROP FUNCTION IF EXISTS documents_fts_trigger()")
    op.drop_table("documents")
    op.drop_table("correspondants")
    op.drop_table("types_document")
    op.drop_table("thematiques")
    op.drop_table("categories")
