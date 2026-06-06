"""Routes des correspondants (externes aux courriers)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import or_, select

from app.api.deps import (
    AgentArchivisteOuPlus,
    AgentCourant,
    AgentSuperviseur,
    IpClient,
    SessionDB,
)
from app.models import Correspondant
from app.schemas.correspondant import (
    CorrespondantCreation,
    CorrespondantLecture,
    CorrespondantMiseAJour,
)
from app.services.audit import journaliser

router = APIRouter(prefix="/correspondants", tags=["correspondants"])


@router.get("", response_model=list[CorrespondantLecture])
async def lister(
    agent: AgentCourant,
    db: SessionDB,
    type_id: int | None = Query(None, description="1=morale, 2=physique"),
    q: str | None = Query(None, description="Recherche libellé"),
    limit: int = Query(100, ge=1, le=500),
) -> list[Correspondant]:
    base = select(Correspondant).where(
        Correspondant.tenant_id == agent.tenant_id,
        Correspondant.actif.is_(True),
    )
    if type_id is not None:
        base = base.where(Correspondant.type_id == type_id)
    if q:
        terme = f"%{q.lower()}%"
        base = base.where(
            or_(
                Correspondant.raison_sociale.ilike(terme),
                Correspondant.nom.ilike(terme),
                Correspondant.prenom.ilike(terme),
            )
        )
    base = base.order_by(
        Correspondant.raison_sociale.asc().nulls_last(),
        Correspondant.nom.asc().nulls_last(),
    ).limit(limit)
    result = await db.execute(base)
    return list(result.scalars())


@router.post(
    "", response_model=CorrespondantLecture, status_code=status.HTTP_201_CREATED
)
async def creer(
    body: CorrespondantCreation,
    agent: AgentArchivisteOuPlus,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Correspondant:
    c = Correspondant(
        tenant_id=agent.tenant_id,
        type_id=body.type_id,
        raison_sociale=body.raison_sociale,
        civilite=body.civilite,
        nom=body.nom,
        prenom=body.prenom,
        fonction=body.fonction,
        adresse=body.adresse,
        telephone=body.telephone,
        email=body.email,
    )
    db.add(c)
    await db.flush()
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="correspondant.create",
        entite="correspondants",
        entite_id=c.id,
        payload={"type_id": body.type_id},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(c)
    return c


@router.put("/{c_id}", response_model=CorrespondantLecture)
async def maj(
    c_id: int,
    body: CorrespondantMiseAJour,
    agent: AgentArchivisteOuPlus,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Correspondant:
    c = await _charger(db, c_id, agent.tenant_id)
    diff: dict[str, object] = {}
    for champ in (
        "raison_sociale",
        "civilite",
        "nom",
        "prenom",
        "fonction",
        "adresse",
        "telephone",
        "email",
    ):
        v = getattr(body, champ)
        if v is not None and v != getattr(c, champ):
            diff[champ] = v
            setattr(c, champ, v)
    if diff:
        await journaliser(
            db,
            tenant_id=agent.tenant_id,
            agent_id=agent.id,
            action="correspondant.update",
            entite="correspondants",
            entite_id=c.id,
            payload={"diff": diff},
            ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
    await db.commit()
    await db.refresh(c)
    return c


@router.delete("/{c_id}", response_model=CorrespondantLecture)
async def desactiver(
    c_id: int,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> Correspondant:
    c = await _charger(db, c_id, superviseur.tenant_id)
    if not c.actif:
        return c
    c.actif = False
    await journaliser(
        db,
        tenant_id=superviseur.tenant_id,
        agent_id=superviseur.id,
        action="correspondant.desactiver",
        entite="correspondants",
        entite_id=c.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(c)
    return c


async def _charger(db, c_id: int, tenant_id: int) -> Correspondant:
    result = await db.execute(
        select(Correspondant).where(
            Correspondant.id == c_id, Correspondant.tenant_id == tenant_id
        )
    )
    c = result.scalar_one_or_none()
    if c is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Correspondant introuvable"
        )
    return c
