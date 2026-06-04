"""Modèle AuditLog — trace append-only des actions sensibles."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditLog(Base):
    """Trace toute action sensible. Jamais mis à jour, jamais supprimé."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    agent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agents.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entite: Mapped[str | None] = mapped_column(String(64))
    entite_id: Mapped[int | None] = mapped_column(BigInteger)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action!r} "
            f"tenant_id={self.tenant_id} ts={self.ts!s}>"
        )
