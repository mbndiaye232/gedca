"""Modèles d'identité : rôles, départements, agents.

Regroupe aussi `TypeCorrespondant` (référentiel statique) — créé dans la
même migration 001 pour minimiser le nombre de scripts Alembic.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class Role(Base):
    """Référentiel statique des rôles. Seedé en migration 001."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(64), nullable=False)

    def __repr__(self) -> str:
        return f"<Role {self.code!r}>"


class TypeCorrespondant(Base):
    """Référentiel statique. `personne_physique` | `personne_morale`. Seedé en 001."""

    __tablename__ = "types_correspondant"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(64), nullable=False)

    def __repr__(self) -> str:
        return f"<TypeCorrespondant {self.code!r}>"


class Departement(Base):
    """Service de l'organisation. Les agents y sont affectés."""

    __tablename__ = "departements"
    __table_args__ = (UniqueConstraint("tenant_id", "libelle", name="uq_departements_tenant_libelle"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str | None] = mapped_column(String(32))
    libelle: Mapped[str] = mapped_column(String(255), nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relations
    tenant: Mapped[Tenant] = relationship(back_populates="departements", lazy="raise")
    agents: Mapped[list[Agent]] = relationship(back_populates="departement", lazy="raise")

    def __repr__(self) -> str:
        return f"<Departement id={self.id} libelle={self.libelle!r}>"


class Agent(Base):
    """Utilisateur du système (vocabulaire métier conservé de l'app desktop)."""

    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "login", name="uq_agents_tenant_login"),
        UniqueConstraint("tenant_id", "email", name="uq_agents_tenant_email"),
        CheckConstraint(
            "auth_provider IN ('local', 'ldap')",
            name="ck_agents_auth_provider",
        ),
        CheckConstraint(
            "auth_provider = 'ldap' OR password_hash IS NOT NULL",
            name="ck_agents_local_has_password",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    login: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    auth_provider: Mapped[str] = mapped_column(
        String(16), nullable=False, default="local", server_default="local"
    )
    nom: Mapped[str] = mapped_column(String(128), nullable=False)
    prenom: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    telephone: Mapped[str | None] = mapped_column(String(64))
    cellulaire: Mapped[str | None] = mapped_column(String(64))
    adresse: Mapped[str | None] = mapped_column(Text)
    photo_chemin: Mapped[str | None] = mapped_column(String(512))
    fonction: Mapped[str | None] = mapped_column(String(128))
    departement_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("departements.id", ondelete="RESTRICT")
    )
    role_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    derniere_connexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relations
    tenant: Mapped[Tenant] = relationship(back_populates="agents", lazy="raise")
    departement: Mapped[Departement | None] = relationship(back_populates="agents", lazy="raise")
    role: Mapped[Role] = relationship(lazy="joined")

    @property
    def nom_complet(self) -> str:
        """Prénom + nom (pour affichage)."""
        return f"{self.prenom} {self.nom}".strip()

    def __repr__(self) -> str:
        return f"<Agent id={self.id} login={self.login!r} tenant_id={self.tenant_id}>"
