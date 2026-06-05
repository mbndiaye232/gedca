"""Tests unitaires du service de stockage chiffré (PRD-02 §5.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services import crypto, storage


# Garantit que la MASTER_KEY est régénérée à chaque test pour ce module —
# le fixture `storage_dir` autouse réinitialise déjà les Settings.


@pytest.mark.asyncio
async def test_stocker_chiffre_et_ecrit_sur_disque(storage_dir: Path) -> None:
    """CA-01 : le fichier brut n'est pas écrit en clair sur disque."""
    contenu = b"Texte ultra confidentiel \xc3\xa9 \xc3\xa0 \xc3\xa7"
    res = await storage.stocker(contenu, tenant_id=1)

    chemin = storage_dir / res.chemin_relatif
    assert chemin.exists()
    octets_disque = chemin.read_bytes()
    # Le contenu brut ne se trouve pas tel quel sur le disque
    assert contenu not in octets_disque
    # En-tête : 12 octets de nonce
    assert len(octets_disque) >= len(contenu) + 12 + 16  # nonce + tag GCM
    assert res.checksum_sha256 == _sha256_hex(contenu)
    assert res.taille_octets == len(contenu)


@pytest.mark.asyncio
async def test_round_trip_chiffrement_meme_tenant(storage_dir: Path) -> None:
    """CA-04 : le contenu déchiffré est identique aux octets d'origine."""
    contenu = b"\x00\x01\x02PDF-MOCK\xff\xfe garbage"
    res = await storage.stocker(contenu, tenant_id=42)

    chunks: list[bytes] = []
    async for ch in storage.stream_dechiffre(res.chemin_relatif, tenant_id=42):
        chunks.append(ch)
    assert b"".join(chunks) == contenu


@pytest.mark.asyncio
async def test_isolation_cle_par_tenant(storage_dir: Path) -> None:
    """Un payload chiffré pour tenant A ne se déchiffre pas pour tenant B."""
    from cryptography.exceptions import InvalidTag

    contenu = b"secret tenant 1"
    res = await storage.stocker(contenu, tenant_id=1)

    with pytest.raises(InvalidTag):
        await storage.lire_dechiffre(res.chemin_relatif, tenant_id=2)


@pytest.mark.asyncio
async def test_stocker_idempotent_par_checksum(storage_dir: Path) -> None:
    """Stocker le même contenu deux fois ne crée pas de fichier différent."""
    contenu = b"abcdef" * 1000
    a = await storage.stocker(contenu, tenant_id=1)
    b = await storage.stocker(contenu, tenant_id=1)
    assert a.checksum_sha256 == b.checksum_sha256
    assert a.chemin_relatif == b.chemin_relatif


@pytest.mark.asyncio
async def test_chemin_inclut_tenant_id(storage_dir: Path) -> None:
    """Sécurité de structure : chaque tenant a son répertoire propre."""
    res = await storage.stocker(b"data", tenant_id=7)
    assert res.chemin_relatif.startswith("7/"), res.chemin_relatif


@pytest.mark.asyncio
async def test_master_key_absente_refuse_au_chiffrement(monkeypatch) -> None:
    """CA-15 : sans MASTER_KEY, l'application refuse de chiffrer."""
    monkeypatch.setenv("MASTER_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    crypto._cle_maitre.cache_clear()
    with pytest.raises(crypto.ConfigurationCryptoError):
        crypto._cle_maitre()


# --- helpers locaux ---------------------------------------------------------


def _sha256_hex(b: bytes) -> str:
    import hashlib

    return hashlib.sha256(b).hexdigest()
