"""Tests des routes référentiels (catégories, thématiques, types) — PRD-02."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models import Agent, Categorie


# ----- Catégories ------------------------------------------------------------


@pytest.mark.asyncio
async def test_archiviste_peut_creer_categorie(
    client: AsyncClient, archiviste: Agent
) -> None:
    """RG-2 §5.10 PRD-02 : création à la volée par un archiviste."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/categories",
        json={"libelle": "Factures"},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 201, response.text
    assert response.json()["libelle"] == "Factures"


@pytest.mark.asyncio
async def test_agent_standard_ne_peut_pas_creer_categorie_403(
    client: AsyncClient, agent_standard: Agent
) -> None:
    """Un agent standard n'a pas le droit de créer des catégories."""
    token = await pytest.jeton_pour(client, agent_standard.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/categories",
        json={"libelle": "Tentative"},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_doublon_categorie_409(
    client: AsyncClient, archiviste: Agent, categorie: Categorie
) -> None:
    """Libellé déjà utilisé dans le tenant → 409."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/categories",
        json={"libelle": categorie.libelle},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_liste_categories_ouverte_a_tous(
    client: AsyncClient, agent_standard: Agent, categorie: Categorie
) -> None:
    """Lecture des catégories ouverte aux agents standards."""
    token = await pytest.jeton_pour(client, agent_standard.login)  # type: ignore[attr-defined]
    response = await client.get(
        "/api/categories", headers=pytest.en_tete_auth(token)  # type: ignore[attr-defined]
    )
    assert response.status_code == 200
    libelles = [c["libelle"] for c in response.json()]
    assert categorie.libelle in libelles


# ----- Thématiques -----------------------------------------------------------


@pytest.mark.asyncio
async def test_archiviste_ne_peut_pas_creer_thematique_403(
    client: AsyncClient, archiviste: Agent
) -> None:
    """Thématiques réservées au superviseur."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/thematiques",
        json={"libelle": "Tentative archi"},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_superviseur_cree_thematique(
    client: AsyncClient, superviseur: Agent
) -> None:
    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/thematiques",
        json={"libelle": "RH"},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 201


# ----- Types de document -----------------------------------------------------


@pytest.mark.asyncio
async def test_superviseur_cree_type_document(
    client: AsyncClient, superviseur: Agent
) -> None:
    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/types-document",
        json={"libelle": "Note de service"},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 201
