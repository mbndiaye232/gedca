"""Tests unitaires des services (crypto, password, jwt, échéances) — sans DB."""

from __future__ import annotations

import base64
import os
import secrets
from datetime import date, timedelta

import pytest

from app.services.echeances import calculer_statut_echeance
from app.services.password import hacher_mot_de_passe, verifier_mot_de_passe


# --- password ----------------------------------------------------------------


def test_hash_bcrypt_verifie() -> None:
    h = hacher_mot_de_passe("Secret123!")
    assert h != "Secret123!"
    assert verifier_mot_de_passe("Secret123!", h)
    assert not verifier_mot_de_passe("WRONG", h)


def test_verifier_avec_hash_none_retourne_false() -> None:
    """Tolérance : agent LDAP sans password_hash → False, pas d'exception."""
    assert verifier_mot_de_passe("anything", None) is False


def test_verifier_avec_hash_malforme_retourne_false() -> None:
    """Hash invalide en base → False, pas de crash."""
    assert verifier_mot_de_passe("anything", "not-a-bcrypt-hash") is False


# --- jwt ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jwt_round_trip() -> None:
    from app.services.jwt import decoder_jeton, emettre_jeton

    token, exp = emettre_jeton(agent_id=42, tenant_id=7, role="superviseur")
    payload = decoder_jeton(token)
    assert payload.agent_id == 42
    assert payload.tenant_id == 7
    assert payload.role == "superviseur"
    assert payload.exp == exp.replace(microsecond=0)  # JWT exp est en seconde


def test_jwt_token_modifie_invalide() -> None:
    from app.services.jwt import JetonInvalideError, decoder_jeton, emettre_jeton

    token, _ = emettre_jeton(agent_id=1, tenant_id=1, role="archiviste")
    # Modifier le payload doit invalider la signature
    parts = token.split(".")
    falsifie = parts[0] + "." + parts[1] + "." + "AAAA" + parts[2][4:]
    with pytest.raises(JetonInvalideError):
        decoder_jeton(falsifie)


# --- crypto ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _set_master_key(monkeypatch):
    """S'assure qu'une MASTER_KEY valide est en place pour les tests crypto."""
    monkeypatch.setenv("MASTER_KEY", base64.b64encode(secrets.token_bytes(32)).decode())
    # Vider le cache de la clé maître pour relire l'env
    from app.services import crypto

    crypto._cle_maitre.cache_clear()
    yield
    crypto._cle_maitre.cache_clear()


def test_crypto_round_trip_meme_tenant() -> None:
    from app.services.crypto import chiffrer, dechiffrer

    plaintext = b"Un secret de test"
    payload = chiffrer(plaintext, tenant_id=1)
    assert payload != plaintext
    assert dechiffrer(payload, tenant_id=1) == plaintext


def test_crypto_cle_differente_par_tenant() -> None:
    """Le ciphertext chiffré pour tenant 1 ne se déchiffre pas pour tenant 2."""
    from cryptography.exceptions import InvalidTag

    from app.services.crypto import chiffrer, dechiffrer

    payload = chiffrer(b"secret", tenant_id=1)
    with pytest.raises(InvalidTag):
        dechiffrer(payload, tenant_id=2)


def test_crypto_master_key_absente_refuse(monkeypatch) -> None:
    from app.services.crypto import ConfigurationCryptoError, _cle_maitre

    monkeypatch.setenv("MASTER_KEY", "")
    # Réinitialiser le cache singleton de Settings
    from app.config import get_settings

    get_settings.cache_clear()
    _cle_maitre.cache_clear()
    with pytest.raises(ConfigurationCryptoError):
        _cle_maitre()
    # Restaurer pour les tests suivants
    monkeypatch.setenv("MASTER_KEY", base64.b64encode(os.urandom(32)).decode())
    get_settings.cache_clear()
    _cle_maitre.cache_clear()


# --- échéances ---------------------------------------------------------------


def test_echeance_sans_date_limite_verte() -> None:
    statut = calculer_statut_echeance(None)
    assert statut.couleur == "vert"
    assert statut.jours_restants is None


def test_echeance_depassee_noir() -> None:
    today = date(2026, 6, 1)
    statut = calculer_statut_echeance(today - timedelta(days=1), aujourd_hui=today)
    assert statut.couleur == "noir"
    assert statut.jours_restants == -1


def test_echeance_lointaine_verte() -> None:
    today = date(2026, 6, 1)
    statut = calculer_statut_echeance(today + timedelta(days=10), aujourd_hui=today)
    assert statut.couleur == "vert"
    assert statut.jours_restants == 10


@pytest.mark.parametrize(
    "jours,couleur_attendue",
    [
        (4, "rouge-clair"),
        (3, "rouge"),
        (2, "rouge"),
        (1, "rouge-fonce"),
        (0, "rouge-fonce"),
    ],
)
def test_echeance_degrade_rouge(jours: int, couleur_attendue: str) -> None:
    today = date(2026, 6, 1)
    statut = calculer_statut_echeance(today + timedelta(days=jours), aujourd_hui=today)
    assert statut.couleur == couleur_attendue
    assert statut.jours_restants == jours
