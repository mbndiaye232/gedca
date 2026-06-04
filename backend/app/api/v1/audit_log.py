"""Consultation des logs d'audit (superviseur uniquement)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import AgentSuperviseur, SessionDB
from app.models import AuditLog
from app.schemas.audit import AuditLogLecture, PageAuditLog

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get(
    "",
    response_model=PageAuditLog,
    summary="Consulter les logs d'audit du tenant (superviseur, paginé)",
)
async def lister(
    superviseur: AgentSuperviseur,
    db: SessionDB,
    action: str | None = Query(None, description="Filtrer par action (ex. 'login')"),
    entite: str | None = Query(None, description="Filtrer par entité (ex. 'agents')"),
    debut: datetime | None = Query(None, description="ts >= debut"),
    fin: datetime | None = Query(None, description="ts <= fin"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> PageAuditLog:
    base = select(AuditLog).where(AuditLog.tenant_id == superviseur.tenant_id)
    base_count = select(func.count(AuditLog.id)).where(
        AuditLog.tenant_id == superviseur.tenant_id
    )

    if action:
        base = base.where(AuditLog.action == action)
        base_count = base_count.where(AuditLog.action == action)
    if entite:
        base = base.where(AuditLog.entite == entite)
        base_count = base_count.where(AuditLog.entite == entite)
    if debut is not None:
        base = base.where(AuditLog.ts >= debut)
        base_count = base_count.where(AuditLog.ts >= debut)
    if fin is not None:
        base = base.where(AuditLog.ts <= fin)
        base_count = base_count.where(AuditLog.ts <= fin)

    total = await db.scalar(base_count) or 0
    result = await db.execute(
        base.order_by(AuditLog.ts.desc()).limit(limit).offset(offset)
    )
    items = [AuditLogLecture.model_validate(row) for row in result.scalars()]
    return PageAuditLog(items=items, total=int(total), limit=limit, offset=offset)
