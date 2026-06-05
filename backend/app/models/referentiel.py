"""Référentiels par tenant : catégories, thématiques, types de document.

Référentiel partagé entre GED (documents) et GEC (courriers). Le superviseur les
gère, mais un archiviste peut créer une catégorie à la volée depuis l'upload.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Categorie(Base):
    """Catégorie de document/courrier (ex. « facture », « rapport »…)."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "libelle", name="uq_categories_tenant_libelle"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    libelle: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Categorie id={self.id} libelle={self.libelle!r}>"


class Thematique(Base):
    """Thématique transverse (ex. « ressources humaines », « contentieux »…)."""

    __tablename__ = "thematiques"
    __table_args__ = (
        UniqueConstraint("tenant_id", "libelle", name="uq_thematiques_tenant_libelle"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    libelle: Mapped[str] = mapped_column(String(128), nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Thematique id={self.id} libelle={self.libelle!r}>"


class TypeDocument(Base):
    """Type de document (ex. « contrat », « note de service »…)."""

    __tablename__ = "types_document"
    __table_args__ = (
        UniqueConstraint("tenant_id", "libelle", name="uq_types_document_tenant_libelle"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    libelle: Mapped[str] = mapped_column(String(128), nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<TypeDocument id={self.id} libelle={self.libelle!r}>"
