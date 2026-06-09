"""Service de réinitialisation de mot de passe par lien email.

Workflow :
1. `creer_token(agent_id, demande_par_id)` — génère un token aléatoire,
   stocke son hash SHA-256, retourne le token brut (à envoyer par email).
2. `verifier_token(token)` — vérifie qu'il existe, n'est pas expiré, ni
   utilisé. Retourne le token en DB (avec agent_id).
3. `consommer_token(token, nouveau_mot_de_passe)` — applique le nouveau
   mdp, marque le token comme utilisé.

Sécurité
- Le token brut n'est jamais stocké en base — seulement son SHA-256.
- Quand un nouveau token est créé pour un agent, les anciens tokens
  actifs sont **invalidés** (marqués utilisés). Ainsi un agent n'a
  qu'un seul lien valide à la fois — la dernière demande gagne.
- Durée de validité : 24h.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TokenResetMdp

# Durée de validité d'un token de reset.
DUREE_VALIDITE = timedelta(hours=24)


def _hash_token(token: str) -> str:
    """SHA-256 hex du token brut."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def creer_token(
    db: AsyncSession, *, agent_id: int, demande_par_id: int | None = None
) -> str:
    """Génère un token, stocke son hash, retourne le token brut.

    Invalide aussi tous les tokens actifs précédents de l'agent.
    """
    # Invalider les anciens tokens actifs (un seul lien valide à la fois)
    now = datetime.now(timezone.utc)
    await db.execute(
        update(TokenResetMdp)
        .where(
            TokenResetMdp.agent_id == agent_id,
            TokenResetMdp.utilise_at.is_(None),
        )
        .values(utilise_at=now)
    )

    # Générer un token aléatoire — 32 octets ≈ 43 caractères URL-safe
    token = secrets.token_urlsafe(32)
    enregistrement = TokenResetMdp(
        agent_id=agent_id,
        token_hash=_hash_token(token),
        expire_at=now + DUREE_VALIDITE,
        demande_par=demande_par_id,
    )
    db.add(enregistrement)
    await db.flush()
    return token


async def verifier_token(
    db: AsyncSession, token: str
) -> TokenResetMdp | None:
    """Renvoie l'enregistrement si le token est valide (existe + non
    expiré + non utilisé), sinon None.

    Volontairement neutre quant à la cause de l'échec (sécurité : ne
    pas distinguer "token inconnu" de "token expiré" pour ne pas
    aider un attaquant à scanner les tokens).
    """
    now = datetime.now(timezone.utc)
    enregistrement = await db.scalar(
        select(TokenResetMdp).where(
            TokenResetMdp.token_hash == _hash_token(token),
            TokenResetMdp.utilise_at.is_(None),
            TokenResetMdp.expire_at > now,
        )
    )
    return enregistrement


async def consommer_token(
    db: AsyncSession, enregistrement: TokenResetMdp
) -> None:
    """Marque un token comme utilisé. À appeler après le changement de mdp."""
    enregistrement.utilise_at = datetime.now(timezone.utc)
