"""Hachage de mot de passe via bcrypt."""

from __future__ import annotations

from passlib.context import CryptContext

# rounds=12 → cible PRD-01 §7. Si l'on monte en charge, garder un rounds élevé
# côté worker mais alléger côté login pour réduire la latence d'authentification.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """Produit un hash bcrypt à stocker en base."""
    return _pwd_context.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str | None) -> bool:
    """Vérifie un mot de passe contre son hash.

    Tolère `hash_stocke=None` (cas d'un agent LDAP sans mot de passe local)
    en retournant False, pour éviter de différencier les codes d'erreur
    selon la cause exacte de l'échec.
    """
    if hash_stocke is None:
        return False
    try:
        return _pwd_context.verify(mot_de_passe, hash_stocke)
    except ValueError:
        # Hash mal formé en base → on traite comme échec, sans crash.
        return False
