"""Modèle Token de réinitialisation de mot de passe."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TokenResetMdp(Base):
    """Token à usage unique pour réinitialiser le mot de passe d'un agent.

    Le token brut n'est jamais stocké — on n'en garde que le hash SHA-256.
    Validé :
    - hash correspond ET
    - non utilisé (`utilise_at IS NULL`) ET
    - non expiré (`expire_at > NOW()`)
    """

    __tablename__ = "tokens_reset_mdp"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    agent_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    cree_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    utilise_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    demande_par: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="SET NULL")
    )
