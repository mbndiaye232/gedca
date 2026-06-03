"""Tests des routes d'administration des agents (CA-05, CA-07, CA-08)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models import Agent


@pytest.mark.asyncio
async def test_superviseur_peut_creer_agent_qui_se_connecte(
    client: AsyncClient, superviseur: Agent, departement
) -> None:
    """CA-14 : superviseur crée un agent → l'agent peut immédiatement se connecter."""
    token_sup = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]

    response = await client.post(
        "/api/agents",
        json={
            "login": "nouveau",
            "mot_de_passe": "Password456!",
            "nom": "Test",
            "prenom": "Nouveau",
            "email": "nouveau@test.local",
            "departement_id": departement.id,
            "role_id": 3,  # agent_standard
        },
        headers=pytest.en_tete_auth(token_sup),  # type: ignore[attr-defined]
    )
    assert response.status_code == 201, response.text

    # Le nouvel agent peut se connecter
    response_login = await client.post(
        "/api/auth/login",
        json={"login": "nouveau", "mot_de_passe": "Password456!"},
    )
    assert response_login.status_code == 200


@pytest.mark.asyncio
async def test_route_superviseur_avec_role_archiviste_403(
    client: AsyncClient, archiviste: Agent
) -> None:
    """CA-05 : archiviste appelle une route superviseur → 403."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    response = await client.get(
        "/api/agents", headers=pytest.en_tete_auth(token)  # type: ignore[attr-defined]
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_creer_agent_login_existant_409(
    client: AsyncClient, superviseur: Agent
) -> None:
    """CA-07 : création avec login déjà pris dans le même tenant → 409."""
    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/agents",
        json={
            "login": superviseur.login,  # déjà pris
            "mot_de_passe": "Password789!",
            "nom": "Dup",
            "prenom": "Test",
            "role_id": 3,
        },
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_desactiver_agent_empeche_connexion(
    client: AsyncClient, superviseur: Agent, archiviste: Agent
) -> None:
    """CA-08 : désactiver un agent → il ne peut plus se connecter."""
    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.post(
        f"/api/agents/{archiviste.id}/desactiver",
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 200

    login_response = await client.post(
        "/api/auth/login",
        json={"login": archiviste.login, "mot_de_passe": "Password123!"},
    )
    assert login_response.status_code == 401


@pytest.mark.asyncio
async def test_superviseur_ne_peut_pas_se_desactiver_lui_meme(
    client: AsyncClient, superviseur: Agent
) -> None:
    """Garde-fou : un superviseur ne peut pas se désactiver lui-même."""
    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.post(
        f"/api/agents/{superviseur.id}/desactiver",
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_agent_lit_son_propre_profil(
    client: AsyncClient, archiviste: Agent
) -> None:
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    response = await client.get(
        "/api/agents/me", headers=pytest.en_tete_auth(token)  # type: ignore[attr-defined]
    )
    assert response.status_code == 200
    body = response.json()
    assert body["login"] == archiviste.login


@pytest.mark.asyncio
async def test_agent_change_son_mot_de_passe(
    client: AsyncClient, archiviste: Agent
) -> None:
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    response = await client.put(
        "/api/agents/me",
        json={
            "mot_de_passe_actuel": "Password123!",
            "nouveau_mot_de_passe": "NouveauMdp456!",
        },
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 200, response.text

    # Ancien mot de passe ne marche plus
    login_ancien = await client.post(
        "/api/auth/login",
        json={"login": archiviste.login, "mot_de_passe": "Password123!"},
    )
    assert login_ancien.status_code == 401

    # Nouveau mot de passe marche
    login_nouveau = await client.post(
        "/api/auth/login",
        json={"login": archiviste.login, "mot_de_passe": "NouveauMdp456!"},
    )
    assert login_nouveau.status_code == 200


@pytest.mark.asyncio
async def test_change_mot_de_passe_avec_mauvais_actuel_400(
    client: AsyncClient, archiviste: Agent
) -> None:
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    response = await client.put(
        "/api/agents/me",
        json={
            "mot_de_passe_actuel": "WRONG",
            "nouveau_mot_de_passe": "NouveauMdp456!",
        },
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 400
