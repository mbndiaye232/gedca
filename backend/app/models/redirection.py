"""Modèles Redirection (PDF docs/redirection.pdf) et AlerteRetardEnvoyee."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Redirection(Base):
    """Redirection d'un agent vers un substitut.

    Un agent absent (`agent_redirige_id`) signale son indisponibilité ; tout
    courrier qui lui était destiné après la création de la redirection ira
    automatiquement chez `agent_substitut_id`. La contrainte
    « une seule redirection active à la fois par agent » est exprimée par
    l'index unique partiel `WHERE active = TRUE` (cf. migration 007).

    Les courriers déjà en cours de traitement avant la création **ne sont
    pas affectés** — c'est le PDF qui le dit (« les courriers en instance
    de traitement avant la redirection ne sont pas concernés »).
    """

    __tablename__ = "redirections"
    __table_args__ = (
        CheckConstraint(
            "agent_redirige_id <> agent_substitut_id",
            name="ck_redirection_substitut_different",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    agent_redirige_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False
    )
    agent_substitut_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False
    )
    cree_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    cree_par: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="SET NULL")
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    supprime_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supprime_par: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="SET NULL")
    )


class AlerteRetardEnvoyee(Base):
    """Trace une alerte de retard envoyée à un agent pour un courrier.

    Sert d'anti-doublon pour le job Celery quotidien : si l'alerte
    `(courrier_id, agent_id, palier)` existe déjà, on ne renvoie pas.
    `palier` ∈ {5, 3, 2, 1, 0} (jours restants à l'échéance).
    """

    __tablename__ = "alertes_retard_envoyees"
    __table_args__ = (
        UniqueConstraint(
            "courrier_id", "agent_id", "palier", name="uq_alertes_retard_unique"
        ),
        CheckConstraint(
            "palier IN (5, 3, 2, 1, 0)",
            name="ck_alertes_retard_palier_valide",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    courrier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("courriers.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    palier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    envoye_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
