"""Modèle Document — cœur du référentiel documentaire GED.

Un document est partagé par les trois modules :
- GED (consultation, recherche)
- GEC (pièce jointe à un courrier)
- Archivage physique (lien optionnel vers un sous-dossier)

Le fichier physique est stocké chiffré AES-256-GCM sur disque,
nommé `{checksum_sha256}.enc`. Le texte OCR et l'embedding restent en clair
en base pour permettre la recherche FTS et sémantique.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Document(Base):
    """Document central — fichier chiffré + métadonnées + index recherche."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "checksum_sha256", name="uq_documents_tenant_checksum"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )

    # Métadonnées descriptives
    titre: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    resume: Mapped[str | None] = mapped_column(Text)
    mots_cles: Mapped[str | None] = mapped_column(Text)

    # Classification
    categorie_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="RESTRICT")
    )
    thematique_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("thematiques.id", ondelete="RESTRICT")
    )
    type_document_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("types_document.id", ondelete="RESTRICT")
    )

    # Fichier
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    taille_octets: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    chemin_stockage: Mapped[str] = mapped_column(Text, nullable=False)
    nonce: Mapped[bytes] = mapped_column(BYTEA, nullable=False)

    # Dates
    date_document: Mapped[date | None] = mapped_column(Date)
    date_numerisation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # OCR + recherche (alimentés par PRD-03 pipeline)
    texte_ocr: Mapped[str | None] = mapped_column(Text)
    recherche_fts: Mapped[Any | None] = mapped_column(TSVECTOR)
    # embedding (pgvector) ajouté en migration ; modèle non-strict pour rester compatible
    # sans dépendre du package python `pgvector` à ce stade.
    # En PRD-03 on importera `from pgvector.sqlalchemy import Vector`.
    # embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))

    # Métadonnées libres. Attribut Python `meta_donnees` pour éviter le clash
    # avec `Base.metadata` (objet MetaData de SQLAlchemy). Colonne DB = "metadata".
    meta_donnees: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
    confidentiel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Provenance
    origine: Mapped[str] = mapped_column(
        String(32), nullable=False, default="upload", server_default="upload"
    )
    statut: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pret", server_default="pret"
    )

    # Audit
    supprime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="SET NULL")
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} titre={self.titre!r}>"


class DocumentVersion(Base):
    """Versions précédentes d'un document — conservées lors d'un remplacement de fichier."""

    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "num_version", name="uq_document_versions_doc_num"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    num_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chemin_stockage: Mapped[str] = mapped_column(Text, nullable=False)
    nonce: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    taille_octets: Mapped[int] = mapped_column(BigInteger, nullable=False)
    commentaire: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="SET NULL")
    )
