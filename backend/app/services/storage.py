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

import asyncio
import hashlib
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from functools import lru_cache
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


# Signatures binaires des formats courants — suffisent à couvrir l'essentiel
# sans dépendre de libmagic (utile en dev Windows où la DLL n'est pas livrée).
_MAGIC_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"%PDF", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
    (b"PK\x03\x04", "application/zip"),  # DOCX/XLSX/ODT (raffiné plus bas)
)


def _detecter_mime(plaintext: bytes) -> str:
    """Détecte le type MIME en inspectant les premiers octets.

    Stratégie :
    1. Match d'une signature binaire connue (formats courants).
    2. Pour les ZIP (`PK\\x03\\x04`), affine en DOCX/XLSX/PPTX/ODT en regardant
       la structure OOXML/ODF dans les 4 Ko.
    3. Fallback `python-magic` si libmagic est disponible (Linux/Docker).
    4. Fallback ultime `application/octet-stream`.
    """
    tete = plaintext[:4096]

    for signature, mime in _MAGIC_SIGNATURES:
        if tete.startswith(signature):
            if mime == "application/zip":
                if b"word/" in tete:
                    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if b"xl/" in tete:
                    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if b"ppt/" in tete:
                    return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                if b"mimetypeapplication/vnd.oasis.opendocument.text" in tete:
                    return "application/vnd.oasis.opendocument.text"
            return mime

    try:
        import magic  # type: ignore[import-not-found]

        detecte = magic.from_buffer(tete, mime=True)
        if detecte:
            return detecte
    except Exception:
        pass

    return "application/octet-stream"


def _chemin_chiffre(tenant_id: int, checksum: str) -> Path:
    """Chemin absolu du fichier chiffré sur disque."""
    return Path(get_settings().storage_root) / str(tenant_id) / f"{checksum}.enc"


def _chemin_relatif(tenant_id: int, checksum: str) -> str:
    return f"{tenant_id}/{checksum}.enc"


# ---------------------------------------------------------------------------
# Backend Cloudflare R2 (compatible S3 via boto3)
# ---------------------------------------------------------------------------
# R2 est sélectionné par STORAGE_BACKEND=r2. Le chemin relatif stocké en base
# (`{tenant_id}/{checksum}.enc`) sert directement de clé d'objet R2 : le code
# appelant (documents.py, courriers.py, worker) reste identique, seul le lieu
# de stockage du blob chiffré change.


@lru_cache(maxsize=1)
def _r2_client():
    """Client boto3 configuré pour Cloudflare R2. Mémoïsé.

    Import paresseux de boto3 pour que les déploiements en stockage local
    n'aient pas à le charger.
    """
    import boto3
    from botocore.config import Config

    s = get_settings()
    endpoint = s.r2_endpoint_url
    if not (endpoint and s.r2_access_key_id and s.r2_secret_access_key and s.r2_bucket):
        raise StorageError(
            "STORAGE_BACKEND=r2 mais configuration R2 incomplète "
            "(R2_ACCOUNT_ID ou R2_ENDPOINT, R2_ACCESS_KEY_ID, "
            "R2_SECRET_ACCESS_KEY, R2_BUCKET)."
        )
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=s.r2_access_key_id,
        aws_secret_access_key=s.r2_secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def _r2_put(key: str, payload: bytes) -> None:
    _r2_client().put_object(Bucket=get_settings().r2_bucket, Key=key, Body=payload)


def _r2_get(key: str) -> bytes:
    from botocore.exceptions import ClientError

    try:
        reponse = _r2_client().get_object(Bucket=get_settings().r2_bucket, Key=key)
    except ClientError as exc:
        raise StorageError(f"Objet R2 introuvable : {key}") from exc
    return reponse["Body"].read()


def _r2_existe(key: str) -> bool:
    from botocore.exceptions import ClientError

    try:
        _r2_client().head_object(Bucket=get_settings().r2_bucket, Key=key)
        return True
    except ClientError:
        return False


def _r2_supprimer(key: str) -> None:
    _r2_client().delete_object(Bucket=get_settings().r2_bucket, Key=key)


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

    # 3. Écriture (idempotente : si le blob existe déjà avec ce checksum,
    #    on ne ré-écrit pas — il a déjà été uploadé).
    key = _chemin_relatif(tenant_id, digest)
    if get_settings().storage_backend == "r2":
        if not await asyncio.to_thread(_r2_existe, key):
            await asyncio.to_thread(_r2_put, key, payload)
    else:
        chemin = _chemin_chiffre(tenant_id, digest)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        if not chemin.exists():
            async with aiofiles.open(chemin, "wb") as fout:
                await fout.write(payload)

    return FichierStocke(
        checksum_sha256=digest,
        taille_octets=len(plaintext),
        mime=mime,
        chemin_relatif=key,
        nonce=nonce,
    )


async def lire_dechiffre(chemin_relatif: str, tenant_id: int) -> bytes:
    """Lit un fichier chiffré et retourne le contenu en clair.

    Pour de gros fichiers, préférer `stream_dechiffre` qui yield par chunks.
    """
    if get_settings().storage_backend == "r2":
        payload = await asyncio.to_thread(_r2_get, chemin_relatif)
    else:
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
    """Supprime un fichier chiffré du stockage (silencieux si absent)."""
    if get_settings().storage_backend == "r2":
        _r2_supprimer(chemin_relatif)
        return
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
