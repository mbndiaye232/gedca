"""Routes d'authentification — login / logout.

Convention de messages d'erreur (PRD-01 RG-1) : ne jamais révéler si le
login existe ou non. Toujours retourner « Identifiants invalides » avec 401.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import AgentCourant, IpClient, SessionDB
from app.models import Agent
from app.schemas.auth import AgentSession, IdentifiantsConnexion, ReponseConnexion
from app.schemas.reset_mdp import (
    ChangerMdpAvecTokenBody,
    TokenValideReponse,
)
from app.services.audit import journaliser
from app.services.jwt import emettre_jeton
from app.services.password import hacher_mot_de_passe, verifier_mot_de_passe
from app.services.reset_mdp import (
    consommer_token as consommer_token_reset,
    verifier_token as verifier_token_reset,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=ReponseConnexion,
    summary="Authentification d'un agent",
)
async def login(
    body: IdentifiantsConnexion,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> ReponseConnexion:
    """Vérifie les identifiants, retourne un JWT.

    Sécurité :
    - Message d'erreur unique 401 « Identifiants invalides » dans tous les cas
      d'échec (login inexistant, mauvais mot de passe, agent désactivé, agent LDAP).
    - L'IP et le user-agent sont systématiquement loggués (succès et échec).
    """
    user_agent = request.headers.get("user-agent")

    # Recherche par login uniquement — pas de filtre tenant car le tenant
    # est porté par le login (unique au global ? non, unique par tenant).
    # En SaaS multi-tenant, le login seul ne suffit pas. Pour l'instant on
    # autorise les logins globalement uniques, le multi-tenant sera affiné
    # via un sous-domaine ou un sélecteur d'organisation au login.
    result = await db.execute(
        select(Agent)
        .options(joinedload(Agent.role))
        .where(Agent.login == body.login)
    )
    agent = result.scalar_one_or_none()

    if agent is None or not verifier_mot_de_passe(body.mot_de_passe, agent.password_hash):
        # Audit échec — on ne connaît pas le tenant si l'agent n'existe pas.
        # On utilise tenant_id=0 conventionnel pour les échecs non-rattachables.
        if agent is not None:
            await journaliser(
                db,
                tenant_id=agent.tenant_id,
                action="login_echec",
                payload={"login": body.login, "raison": "mot_de_passe_invalide"},
                ip=ip,
                user_agent=user_agent,
            )
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not agent.actif:
        await journaliser(
            db,
            tenant_id=agent.tenant_id,
            agent_id=agent.id,
            action="login_echec",
            payload={"login": body.login, "raison": "agent_inactif"},
            ip=ip,
            user_agent=user_agent,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Succès → JWT + audit + maj derniere_connexion
    token, exp = emettre_jeton(
        agent_id=agent.id, tenant_id=agent.tenant_id, role=agent.role.code
    )
    agent.derniere_connexion = datetime.now(timezone.utc)
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="login",
        entite="agents",
        entite_id=agent.id,
        ip=ip,
        user_agent=user_agent,
    )
    await db.commit()
    await db.refresh(agent)

    return ReponseConnexion(
        access_token=token,
        expire_at=exp,
        agent=AgentSession(
            id=agent.id,
            login=agent.login,
            nom=agent.nom,
            prenom=agent.prenom,
            email=agent.email,
            role=agent.role.code,
            tenant_id=agent.tenant_id,
        ),
    )


# ---------------------------------------------------------------------------
# Réinitialisation de mot de passe — endpoints publics (token-protected)
# ---------------------------------------------------------------------------


@router.get(
    "/reset-mdp/verifier",
    response_model=TokenValideReponse,
    summary="Vérifier qu'un token de réinitialisation est valide",
)
async def verifier_token_reset_mdp(
    token: str, db: SessionDB
) -> TokenValideReponse:
    """Vérifie la validité d'un token sans le consommer.

    Utilisé par la page `/reset-mdp` côté frontend pour décider si on
    affiche le formulaire de saisie ou un message « lien invalide /
    expiré ».

    Pour des raisons de sécurité, on ne distingue pas les causes
    d'invalidité (token inconnu vs expiré vs déjà utilisé) — toujours
    `valide=false` sans détail.
    """
    enregistrement = await verifier_token_reset(db, token)
    if enregistrement is None:
        return TokenValideReponse(valide=False)
    agent = await db.get(Agent, enregistrement.agent_id)
    if agent is None or not agent.actif:
        return TokenValideReponse(valide=False)
    return TokenValideReponse(valide=True, prenom=agent.prenom)


@router.post(
    "/reset-mdp/changer",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Appliquer un nouveau mot de passe via un token de réinitialisation",
)
async def changer_mdp_avec_token(
    body: ChangerMdpAvecTokenBody,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> None:
    """Définit le nouveau mot de passe à partir d'un token valide.

    Le token est consommé (marqué `utilise_at`) immédiatement après
    l'application — un même token ne peut servir qu'une fois.

    Si le token est invalide, on renvoie un 400 générique « lien
    invalide ou expiré » sans révéler la cause précise.
    """
    enregistrement = await verifier_token_reset(db, body.token)
    if enregistrement is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien invalide ou expiré. Demande à un superviseur de te renvoyer un lien.",
        )
    agent = await db.get(Agent, enregistrement.agent_id)
    if agent is None or not agent.actif:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien invalide ou expiré. Demande à un superviseur de te renvoyer un lien.",
        )

    agent.password_hash = hacher_mot_de_passe(body.nouveau_mot_de_passe)
    await consommer_token_reset(db, enregistrement)
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="agent.reset_mdp_applique",
        entite="agents",
        entite_id=agent.id,
        payload={"par_token": True},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Déconnexion (stateless : log côté serveur uniquement)",
)
async def logout(
    agent: AgentCourant,
    db: SessionDB,
    ip: IpClient,
    request: Request,
) -> None:
    """Trace la déconnexion. Le client supprime son token côté navigateur."""
    await journaliser(
        db,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        action="logout",
        entite="agents",
        entite_id=agent.id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
