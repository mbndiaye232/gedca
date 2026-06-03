"""Signature et vérification des JWT."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import get_settings


@dataclass(frozen=True, slots=True)
class JetonDecode:
    """Données extraites d'un JWT valide."""

    agent_id: int
    tenant_id: int
    role: str
    exp: datetime


class JetonInvalideError(Exception):
    """Levée quand un JWT est expiré, mal signé ou mal formé."""


def emettre_jeton(*, agent_id: int, tenant_id: int, role: str) -> tuple[str, datetime]:
    """Émet un JWT pour un agent authentifié. Retourne (token, expiration UTC)."""
    settings = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(agent_id),
        "tid": tenant_id,
        "role": role,
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, exp


def decoder_jeton(token: str) -> JetonDecode:
    """Vérifie la signature et l'expiration. Lève JetonInvalideError sinon."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise JetonInvalideError(str(exc)) from exc

    try:
        return JetonDecode(
            agent_id=int(payload["sub"]),
            tenant_id=int(payload["tid"]),
            role=str(payload["role"]),
            exp=datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise JetonInvalideError(f"Payload JWT invalide : {exc}") from exc
