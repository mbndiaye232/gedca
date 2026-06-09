"""Routes Redirection (PDF docs/redirection.pdf).

- POST   /api/redirections                  : créer ma redirection
- GET    /api/redirections/me               : ma redirection active (ou null)
- DELETE /api/redirections/{id}             : supprimer (la mienne ou superviseur)
- GET    /api/redirections                  : liste de toutes (superviseur)
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import (
    AgentCourant,
    AgentSuperviseur,
    IpClient,
    SessionDB,
)
from app.models import Agent, Redirection
from app.schemas.redirection import (
    AgentMini,
    RedirectionCreation,
    RedirectionDetail,
    RedirectionLecture,
)
from app.services.audit import journaliser

router = APIRouter(prefix="/redirections", tags=["redirections"])


async def _enrichir(
    db: SessionDB, r: Redirection
) -> RedirectionDetail:
    """Charge les mini-profils des agents impliqués."""
    redirige = await db.get(Agent, r.agent_redirige_id)
    substitut = await db.get(Agent, r.agent_substitut_id)
    return RedirectionDetail(
        id=r.id,
        agent_redirige_id=r.agent_redirige_id,
        agent_substitut_id=r.agent_substitut_id,
        cree_at=r.cree_at,
        cree_par=r.cree_par,
        active=r.active,
        supprime_at=r.supprime_at,
        supprime_par=r.supprime_par,
        agent_redirige=AgentMini.model_validate(redirige) if redirige else None,
        agent_substitut=AgentMini.model_validate(substitut) if substitut else None,
    )


# ---------------------------------------------------------------------------
# Self-service
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=RedirectionDetail | None,
    summary="Ma redirection active (None si je n'en ai pas)",
)
async def ma_redirection(
    agent: AgentCourant, db: SessionDB
) -> RedirectionDetail | None:
    r = await db.scalar(
        select(Redirection).where(
            Redirection.tenant_id == agent.tenant_id,
            Redirection.agent_redirige_id == agent.id,
            Redirection.active.is_(True),
        )
    )
    if r is None:
        return None
    return await _enrichir(db, r)


@router.post(
    "",
    response_model=RedirectionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Créer ma redirection vers un substitut",
)
async def creer(
    body: RedirectionCreation,
    agent: AgentCourant,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> RedirectionDetail:
    """Crée ma redirection (PDF p. 1).

    Préconditions :
    - Je ne peux pas me rediriger vers moi-même
    - Je dois ne PAS avoir de redirection active (sinon supprimer la
      précédente d'abord — règle "une seule redirection à la fois")
    - L'agent substitut doit exister, être du même tenant, et être actif
    """
    if body.agent_substitut_id == agent.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tu ne peux pas te désigner comme ton propre substitut.",
        )

    substitut = await db.scalar(
        select(Agent).where(
            Agent.id == body.agent_substitut_id,
            Agent.tenant_id == agent.tenant_id,
            Agent.actif.is_(True),
        )
    )
    if substitut is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent substitut introuvable ou désactivé.",
        )

    # Vérif explicite (en plus de l'index unique partiel qui ferait la
    # même chose côté DB, mais avec une erreur SQLAlchemy moins lisible)
    deja = await db.scalar(
        select(Redirection).where(
            Redirection.tenant_id == agent.tenant_id,
            Redirection.agent_redirige_id == agent.id,
            Redirection.active.is_(True),
        )
    )
    if deja is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Tu as déjà une redirection active. Supprime-la avant d'en "
                "créer une nouvelle."
            ),
        )

    nouvelle = Redirection(
        tenant_id=agent.tenant_id,
        agent_redirige_id=agent.id,
        agent_substitut_id=body.agent_substitut_id,
        cree_par=agent.id,
        active=True,
    )
    db.add(nouvelle)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflit lors de la création : {exc.orig}",
        ) from exc

    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="redirection.creation",
        entite="redirections",
        entite_id=nouvelle.id,
        payload={"agent_substitut_id": body.agent_substitut_id},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(nouvelle)
    return await _enrichir(db, nouvelle)


@router.delete(
    "/{redirection_id}",
    response_model=RedirectionDetail,
    summary="Supprimer une redirection (le redirigé lui-même ou superviseur)",
)
async def supprimer(
    redirection_id: int,
    agent: AgentCourant,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> RedirectionDetail:
    """Désactive la redirection (soft delete via `active=False`).

    Autorisé pour :
    - L'agent redirigé lui-même (cas standard : il rentre de congés)
    - Un superviseur (cas d'urgence : l'agent absent ne peut pas se
      reconnecter pour supprimer sa redirection)
    """
    r = await db.scalar(
        select(Redirection).where(
            Redirection.id == redirection_id,
            Redirection.tenant_id == agent.tenant_id,
        )
    )
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Redirection introuvable.",
        )
    if not r.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette redirection est déjà désactivée.",
        )

    est_proprio = r.agent_redirige_id == agent.id
    est_superviseur = agent.role.code == "superviseur"
    if not est_proprio and not est_superviseur:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Seul l'agent redirigé ou un superviseur peut supprimer "
                "cette redirection."
            ),
        )

    r.active = False
    r.supprime_at = datetime.now(timezone.utc)
    r.supprime_par = agent.id

    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="redirection.suppression",
        entite="redirections",
        entite_id=r.id,
        payload={
            "agent_redirige_id": r.agent_redirige_id,
            "agent_substitut_id": r.agent_substitut_id,
        },
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(r)
    return await _enrichir(db, r)


# ---------------------------------------------------------------------------
# Vue superviseur
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[RedirectionDetail],
    summary="Lister toutes les redirections actives du tenant (superviseur)",
)
async def lister(
    superviseur: AgentSuperviseur, db: SessionDB
) -> list[RedirectionDetail]:
    result = await db.execute(
        select(Redirection)
        .where(
            Redirection.tenant_id == superviseur.tenant_id,
            Redirection.active.is_(True),
        )
        .order_by(Redirection.cree_at.desc())
    )
    return [await _enrichir(db, r) for r in result.scalars()]
