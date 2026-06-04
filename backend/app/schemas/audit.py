"""Schémas Pydantic pour audit_log."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogLecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int | None
    action: str
    entite: str | None
    entite_id: int | None
    payload: dict[str, Any]
    ip: str | None
    user_agent: str | None
    ts: datetime


class PageAuditLog(BaseModel):
    """Pagination simple."""

    items: list[AuditLogLecture]
    total: int
    limit: int
    offset: int
