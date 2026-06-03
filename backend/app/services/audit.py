"""Service d'écriture dans audit_log — append-only.

Toute action sensible passe par `journaliser()`. Le service est synchrone
en écriture (pas de fire-and-forget en v1) pour garantir que l'audit ne
soit jamais perdu en cas de crash après la réponse HTTP.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def journaliser(
    db: AsyncSession,
    *,
    tenant_id: int,
    action: str,
    agent_id: int | None = None,
    entite: str | None = None,
    entite_id: int | None = None,
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Crée une ligne dans audit_log.

    Le caller est responsable du commit de la session. Cela permet de
    grouper l'audit avec l'action métier (ex. login + update derniere_connexion)
    dans la même transaction.
    """
    entry = AuditLog(
        tenant_id=tenant_id,
        agent_id=agent_id,
        action=action,
        entite=entite,
        entite_id=entite_id,
        payload=payload or {},
        ip=ip,
        user_agent=user_agent,
    )
    db.add(entry)
    return entry
