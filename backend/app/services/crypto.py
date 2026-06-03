"""Service de chiffrement — clé maître + dérivation par tenant (HKDF) + AES-256-GCM.

Utilisé par :
- PRD-01 : chiffrement des mots de passe SMTP/IMAP par tenant (`tenants.smtp_password_enc`).
- PRD-02 : chiffrement des documents au repos.

La clé maître est lue depuis `MASTER_KEY` (32 octets en base64). Si absente
ou mal formée, l'application refuse de démarrer (vérification au premier
appel).
"""

from __future__ import annotations

import base64
import os
from functools import lru_cache

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.config import get_settings

NONCE_TAILLE = 12  # AES-GCM standard
TAG_TAILLE = 16  # auth_tag AES-GCM


class ConfigurationCryptoError(RuntimeError):
    """Configuration cryptographique invalide (MASTER_KEY absente ou mal formée)."""


@lru_cache(maxsize=1)
def _cle_maitre() -> bytes:
    """Décode et valide la MASTER_KEY. Mémoïsée.

    Lève ConfigurationCryptoError si la clé est absente, mal encodée
    ou n'a pas la taille attendue (32 octets).
    """
    raw = get_settings().master_key
    if not raw:
        raise ConfigurationCryptoError("MASTER_KEY absente de la configuration.")
    try:
        cle = base64.b64decode(raw, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ConfigurationCryptoError(
            "MASTER_KEY mal encodée (attendu : base64 standard)."
        ) from exc
    if len(cle) != 32:
        raise ConfigurationCryptoError(
            f"MASTER_KEY de taille {len(cle)} octets, 32 attendus."
        )
    return cle


def _cle_tenant(tenant_id: int, *, usage: str = "documents") -> bytes:
    """Dérive une clé spécifique au tenant via HKDF-SHA-256.

    Le paramètre `usage` permet d'isoler les usages cryptographiques
    (`documents`, `smtp`, etc.) sous une même clé maître.
    """
    info = f"gedca-{usage}-{tenant_id}".encode()
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info)
    return hkdf.derive(_cle_maitre())


def chiffrer(plaintext: bytes, tenant_id: int, *, usage: str = "documents") -> bytes:
    """Chiffre `plaintext` avec la clé dérivée du tenant.

    Retourne `nonce (12 octets) || ciphertext || auth_tag (16 octets)`.
    Format auto-portant — le nonce est inclus, pas besoin de le stocker à part.
    """
    nonce = os.urandom(NONCE_TAILLE)
    aesgcm = AESGCM(_cle_tenant(tenant_id, usage=usage))
    ct = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return nonce + ct


def dechiffrer(payload: bytes, tenant_id: int, *, usage: str = "documents") -> bytes:
    """Déchiffre un payload produit par `chiffrer`.

    Lève `cryptography.exceptions.InvalidTag` si l'authentification échoue
    (clé incorrecte, payload altéré).
    """
    if len(payload) < NONCE_TAILLE + TAG_TAILLE:
        raise ValueError("Payload chiffré trop court pour contenir nonce + tag.")
    nonce, ct = payload[:NONCE_TAILLE], payload[NONCE_TAILLE:]
    aesgcm = AESGCM(_cle_tenant(tenant_id, usage=usage))
    return aesgcm.decrypt(nonce, ct, associated_data=None)
