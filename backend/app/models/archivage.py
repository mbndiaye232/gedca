"""Modèles de l'archivage physique — 6 niveaux hiérarchiques.

Codification dotée automatique : `SS.LL.RR.BBB.DD.SD`. Les numéros sont
attribués par séquence par parent (jamais saisis par l'utilisateur).

Site (2 chiffres) → LocalSalle (2) → Rayon (2) → Boite (3) → DossiersClasseurs (2)
                                                                       → SousDossiers (2)

Le code complet n'est jamais stocké — il est calculé à la volée via la vue
SQL `v_sous_dossiers_code` (cf. migration).
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Site(Base):
    """Site géographique d'archivage (niveau 1)."""

    __tablename__ = "sites"
    __table_args__ = (
        UniqueConstraint("tenant_id", "numero", name="uq_sites_tenant_numero"),
        UniqueConstraint("tenant_id", "libelle", name="uq_sites_tenant_libelle"),
        CheckConstraint("numero BETWEEN 1 AND 99", name="ck_sites_numero_range"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<Site #{self.numero:02d} {self.libelle!r}>"


class LocalSalle(Base):
    """Local / salle au sein d'un site (niveau 2)."""

    __tablename__ = "locaux_salles"
    __table_args__ = (
        UniqueConstraint("site_id", "numero", name="uq_locaux_site_numero"),
        UniqueConstraint("site_id", "libelle", name="uq_locaux_site_libelle"),
        CheckConstraint("numero BETWEEN 1 AND 99", name="ck_locaux_numero_range"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    site_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False
    )
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class Rayon(Base):
    """Rayon au sein d'un local (niveau 3)."""

    __tablename__ = "rayons"
    __table_args__ = (
        UniqueConstraint("local_id", "numero", name="uq_rayons_local_numero"),
        UniqueConstraint("local_id", "libelle", name="uq_rayons_local_libelle"),
        CheckConstraint("numero BETWEEN 1 AND 99", name="ck_rayons_numero_range"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    local_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("locaux_salles.id", ondelete="RESTRICT"), nullable=False
    )
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)


class Boite(Base):
    """Boîte au sein d'un rayon (niveau 4) — 3 chiffres, jusqu'à 999."""

    __tablename__ = "boites"
    __table_args__ = (
        UniqueConstraint("rayon_id", "numero", name="uq_boites_rayon_numero"),
        UniqueConstraint("rayon_id", "libelle", name="uq_boites_rayon_libelle"),
        CheckConstraint("numero BETWEEN 1 AND 999", name="ck_boites_numero_range"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rayon_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("rayons.id", ondelete="RESTRICT"), nullable=False
    )
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)


class DossierClasseur(Base):
    """Dossier classeur au sein d'une boîte (niveau 5)."""

    __tablename__ = "dossiers_classeurs"
    __table_args__ = (
        UniqueConstraint("boite_id", "numero", name="uq_dossiers_boite_numero"),
        UniqueConstraint("boite_id", "libelle", name="uq_dossiers_boite_libelle"),
        CheckConstraint("numero BETWEEN 1 AND 99", name="ck_dossiers_numero_range"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    boite_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("boites.id", ondelete="RESTRICT"), nullable=False
    )
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)


class SousDossier(Base):
    """Sous-dossier au sein d'un dossier (niveau 6, le plus fin)."""

    __tablename__ = "sous_dossiers"
    __table_args__ = (
        UniqueConstraint("dossier_id", "numero", name="uq_sous_dossiers_dossier_numero"),
        UniqueConstraint(
            "dossier_id", "libelle", name="uq_sous_dossiers_dossier_libelle"
        ),
        CheckConstraint("numero BETWEEN 1 AND 99", name="ck_sous_dossiers_numero_range"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dossier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dossiers_classeurs.id", ondelete="RESTRICT"), nullable=False
    )
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)


class DocumentSousDossier(Base):
    """Lien M:N entre un document et un sous-dossier d'archivage physique."""

    __tablename__ = "documents_sous_dossiers"

    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    sous_dossier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sous_dossiers.id", ondelete="RESTRICT"), primary_key=True
    )
