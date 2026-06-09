"""Modèles SQLAlchemy du module GEC (PRD-06A).

Tables couvertes :
- Courrier (cœur)
- CopieCourrier (M:N agents en copie)
- Imputation (historique des transferts de propriété)
- NoteCourrier (post-it)
- HistoriqueCourrier (timeline visible utilisateur)
- DocumentCourrier (M:N pièces additionnelles)
- StatutCourrier, ActionCourrier (référentiels statiques)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.correspondant import Correspondant
    from app.models.document import Document


# Réutilise l'ENUM PostgreSQL créé par la migration 005, ne pas recréer.
SensCourrierEnum = ENUM(
    "entrant",
    "sortant",
    "interne",
    name="sens_courrier",
    create_type=False,
)


class StatutCourrier(Base):
    """Référentiel statique des statuts. Seedé en migration 005."""

    __tablename__ = "statuts_courrier"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(64), nullable=False)

    def __repr__(self) -> str:
        return f"<StatutCourrier {self.code!r}>"


class ActionCourrier(Base):
    """Référentiel statique des actions du workflow GEC. Seedé en migration 005."""

    __tablename__ = "actions_courrier"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    libelle: Mapped[str] = mapped_column(String(64), nullable=False)

    def __repr__(self) -> str:
        return f"<ActionCourrier {self.code!r}>"


class Courrier(Base):
    """Un courrier enregistré dans la GEC."""

    __tablename__ = "courriers"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "numero_enregistrement", name="uq_courriers_tenant_numero"
        ),
        CheckConstraint(
            "(sens = 'interne') OR (correspondant_id IS NOT NULL)",
            name="ck_courriers_correspondant_si_externe",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    numero_enregistrement: Mapped[str] = mapped_column(String(16), nullable=False)
    sens: Mapped[str] = mapped_column(SensCourrierEnum, nullable=False)
    ref_externe: Mapped[str | None] = mapped_column(String(128))
    categorie_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="RESTRICT")
    )
    objet: Mapped[str] = mapped_column(Text, nullable=False)
    mots_cles: Mapped[str | None] = mapped_column(Text)
    observations: Mapped[str | None] = mapped_column(Text)

    date_courrier: Mapped[date | None] = mapped_column(Date)
    date_arrivee: Mapped[date | None] = mapped_column(Date)
    date_limite: Mapped[date | None] = mapped_column(Date)

    correspondant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("correspondants.id", ondelete="RESTRICT")
    )
    departement_destinataire_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("departements.id", ondelete="RESTRICT")
    )
    agent_destinataire_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False
    )

    # Pièce principale obligatoire (décision PRD-06A)
    document_principal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
    )

    statut_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("statuts_courrier.id", ondelete="RESTRICT"),
        nullable=False,
    )
    agent_proprietaire_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False
    )

    courrier_origine_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("courriers.id", ondelete="SET NULL")
    )

    # PRD-06B : workflow de validation
    # - NULL tant qu'aucune demande de validation n'a été émise
    # - Rempli au moment de "Demander une validation" (qui doit valider)
    # - Reste rempli après "Valider" (info historique)
    agent_valideur_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="RESTRICT")
    )

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

    # Relations utiles (lazy="raise" pour forcer les selectinload explicites)
    statut: Mapped[StatutCourrier] = relationship(lazy="joined")
    document_principal: Mapped[Document] = relationship(
        foreign_keys=[document_principal_id], lazy="joined"
    )
    correspondant: Mapped[Correspondant | None] = relationship(lazy="joined")
    agent_destinataire: Mapped[Agent] = relationship(
        foreign_keys=[agent_destinataire_id], lazy="raise"
    )
    agent_proprietaire: Mapped[Agent] = relationship(
        foreign_keys=[agent_proprietaire_id], lazy="raise"
    )

    def __repr__(self) -> str:
        return f"<Courrier {self.numero_enregistrement} ({self.sens})>"


class CopieCourrier(Base):
    """Lien M:N : agents en copie d'un courrier."""

    __tablename__ = "copies_courriers"

    courrier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("courriers.id", ondelete="CASCADE"), primary_key=True
    )
    agent_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    lu: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ajoute_par: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="SET NULL")
    )
    ajoute_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Imputation(Base):
    """Historique d'un transfert de propriété (imputation)."""

    __tablename__ = "imputations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    courrier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("courriers.id", ondelete="CASCADE"), nullable=False
    )
    agent_imputeur_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False
    )
    agent_impute_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False
    )
    instruction: Mapped[str | None] = mapped_column(Text)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NoteCourrier(Base):
    """Post-it électronique sur un courrier."""

    __tablename__ = "notes_courrier"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    courrier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("courriers.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="SET NULL")
    )
    contenu: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class HistoriqueCourrier(Base):
    """Timeline visible par l'utilisateur (qui, quoi, quand)."""

    __tablename__ = "historiques_courrier"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    courrier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("courriers.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="SET NULL")
    )
    action_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("actions_courrier.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    action: Mapped[ActionCourrier] = relationship(lazy="joined")


class DocumentCourrier(Base):
    """Lien M:N entre courrier et document additionnel (pièces jointes)."""

    __tablename__ = "documents_courrier"

    courrier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("courriers.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documents.id", ondelete="RESTRICT"), primary_key=True
    )
    ajoute_par: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="SET NULL")
    )
    ajoute_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
