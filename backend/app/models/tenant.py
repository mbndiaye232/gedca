"""Modèle Tenant — organisation cliente (multi-tenant)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.agent import Agent, Departement


class Tenant(Base):
    """Une organisation cliente. En mode on-prem, il n'y en a qu'un seul (`id=1`)."""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    raison_sociale: Mapped[str] = mapped_column(String(255), nullable=False)
    adresse: Mapped[str | None] = mapped_column(Text)
    telephone: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(255))
    logo_chemin: Mapped[str | None] = mapped_column(Text)

    # SMTP — mot de passe chiffré avec la clé maître
    smtp_host: Mapped[str | None] = mapped_column(String(255))
    smtp_port: Mapped[int | None] = mapped_column(Integer)
    smtp_user: Mapped[str | None] = mapped_column(String(255))
    smtp_password_enc: Mapped[bytes | None] = mapped_column(BYTEA)
    smtp_from: Mapped[str | None] = mapped_column(String(255))
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True)

    # IA
    ai_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="anthropic")
    ai_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Alertes
    delai_alerte_jours: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    # Méta
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
    agents: Mapped[list[Agent]] = relationship(
        back_populates="tenant", cascade="all", lazy="raise"
    )
    departements: Mapped[list[Departement]] = relationship(
        back_populates="tenant", cascade="all", lazy="raise"
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} code={self.code!r}>"
