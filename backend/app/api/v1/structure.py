"""Routes de gestion de la structure (tenant courant — vue superviseur)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import (
    AgentCourant,
    AgentSuperviseur,
    IpClient,
    SessionDB,
)
from app.models import Tenant
from app.schemas.structure import StructureLecture, StructureMiseAJour
from app.services.audit import journaliser

router = APIRouter(prefix="/structure", tags=["structure"])


@router.get(
    "",
    response_model=StructureLecture,
    summary="Lire les infos de l'organisation (tenant courant)",
)
async def lire(agent: AgentCourant, db: SessionDB) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == agent.tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        # Devrait être impossible si le JWT est cohérent avec la base
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant introuvable"
        )
    return tenant


@router.put(
    "",
    response_model=StructureLecture,
    summary="Modifier les infos de l'organisation (superviseur)",
)
async def maj(
    body: StructureMiseAJour,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == superviseur.tenant_id))
    tenant = result.scalar_one()
    diff: dict[str, object] = {}
    for champ in ("raison_sociale", "adresse", "telephone", "email", "logo_chemin"):
        nouvelle = getattr(body, champ)
        if nouvelle is not None and nouvelle != getattr(tenant, champ):
            diff[champ] = nouvelle
            setattr(tenant, champ, nouvelle)

    if not diff:
        return tenant

    await journaliser(
        db,
        tenant_id=tenant.id,
        agent_id=superviseur.id,
        action="structure.update",
        entite="tenants",
        entite_id=tenant.id,
        payload={"diff": diff},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(tenant)
    return tenant
