"""Service de stockage de fichiers chiffrés.

Responsable de :
- Calcul du SHA-256 d'un upload (en streaming, mémoire bornée).
- Chiffrement AES-256-GCM (via `app.services.crypto`) avec clé dérivée par tenant.
- Écriture sur disque sous `{STORAGE_ROOT}/{tenant_id}/{checksum}.enc`.
- Déchiffrement en streaming pour la visionneuse.
- Détection MIME serveur via `python-magic` (jamais la valeur fournie par le client).

Format du fichier sur disque :
    nonce (12 octets) || ciphertext || auth_tag (16 octets)

`chiffrer`/`dechiffrer` de `crypto.py` encapsulent déjà ce format ; ici on
ajoute l'orchestration disque + métadonnées.
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from pathlib import Path

import aiofiles

from app.config import get_settings
from app.services.crypto import NONCE_TAILLE, chiffrer, dechiffrer


@dataclass(frozen=True, slots=True)
class FichierStocke:
    """Métadonnées d'un fichier stocké, retournées par `stocker`."""

    checksum_sha256: str
    taille_octets: int
    mime: str
    chemin_relatif: str  # relatif à STORAGE_ROOT
    nonce: bytes


class StorageError(RuntimeError):
    """Erreur d'IO ou de chiffrement côté stockage."""


def _detecter_mime(plaintext: bytes) -> str:
    """Détecte le type MIME serveur en inspectant les premiers octets.

    Utilise `python-magic` si disponible, sinon retourne `application/octet-stream`.
    """
    try:
        import magic  # type: ignore[import-not-found]

        return magic.from_buffer(plaintext[:4096], mime=True) or "application/octet-stream"
    except (ImportError, Exception):
        return "application/octet-stream"


def _chemin_chiffre(tenant_id: int, checksum: str) -> Path:
    """Chemin absolu du fichier chiffré sur disque."""
    return Path(get_settings().storage_root) / str(tenant_id) / f"{checksum}.enc"


def _chemin_relatif(tenant_id: int, checksum: str) -> str:
    return f"{tenant_id}/{checksum}.enc"


async def stocker(plaintext: bytes, tenant_id: int) -> FichierStocke:
    """Chiffre et écrit un buffer sur disque. Idempotent par checksum.

    Args:
        plaintext: contenu en clair du fichier reçu.
        tenant_id: tenant propriétaire (sert à dériver la clé HKDF).

    Returns:
        Métadonnées prêtes à insérer dans `documents`.
    """
    # 1. checksum + détection MIME
    digest = hashlib.sha256(plaintext).hexdigest()
    mime = _detecter_mime(plaintext)

    # 2. Chiffrement
    payload = chiffrer(plaintext, tenant_id=tenant_id, usage="documents")
    nonce = payload[:NONCE_TAILLE]

    # 3. Écriture disque (idempotente : si le fichier existe déjà avec ce
    #    checksum, on ne ré-écrit pas — il a déjà été uploadé.)
    chemin = _chemin_chiffre(tenant_id, digest)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if not chemin.exists():
        async with aiofiles.open(chemin, "wb") as fout:
            await fout.write(payload)

    return FichierStocke(
        checksum_sha256=digest,
        taille_octets=len(plaintext),
        mime=mime,
        chemin_relatif=_chemin_relatif(tenant_id, digest),
        nonce=nonce,
    )


async def lire_dechiffre(chemin_relatif: str, tenant_id: int) -> bytes:
    """Lit un fichier chiffré et retourne le contenu en clair.

    Pour de gros fichiers, préférer `stream_dechiffre` qui yield par chunks.
    """
    chemin = Path(get_settings().storage_root) / chemin_relatif
    if not chemin.exists():
        raise StorageError(f"Fichier introuvable : {chemin_relatif}")
    async with aiofiles.open(chemin, "rb") as fin:
        payload = await fin.read()
    return dechiffrer(payload, tenant_id=tenant_id, usage="documents")


async def stream_dechiffre(
    chemin_relatif: str, tenant_id: int, chunk_size: int = 64 * 1024
) -> AsyncIterator[bytes]:
    """Génère le contenu déchiffré par chunks (streaming).

    Pratique pour `StreamingResponse` FastAPI. NB : AES-GCM ne supporte pas
    le streaming natif (l'auth tag est en fin), donc on déchiffre en mémoire
    puis on yield par tranches. Acceptable jusqu'à des fichiers de l'ordre
    de centaines de Mo.
    """
    clair = await lire_dechiffre(chemin_relatif, tenant_id)
    for i in range(0, len(clair), chunk_size):
        yield clair[i : i + chunk_size]


def supprimer_fichier(chemin_relatif: str) -> None:
    """Supprime un fichier chiffré du disque (silencieux si absent)."""
    chemin = Path(get_settings().storage_root) / chemin_relatif
    if chemin.exists():
        chemin.unlink()


async def calculer_checksum_streaming(stream: Iterable[bytes]) -> tuple[str, bytes]:
    """Calcule SHA-256 + accumule le contenu depuis un iterable.

    Utile pour les uploads FastAPI où on ne veut pas charger tout en RAM
    avant de vérifier la déduplication. Retourne `(checksum, contenu)`.
    """
    sha = hashlib.sha256()
    buf = bytearray()
    for chunk in stream:
        sha.update(chunk)
        buf.extend(chunk)
    return sha.hexdigest(), bytes(buf)
