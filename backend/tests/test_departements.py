"""Tests de gestion des départements (CA-11)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Departement


@pytest.mark.asyncio
async def test_creer_et_lister_departements(
    client: AsyncClient, superviseur: Agent
) -> None:
    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/departements",
        json={"libelle": "Comptabilité"},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 201, response.text

    response = await client.get(
        "/api/departements", headers=pytest.en_tete_auth(token)  # type: ignore[attr-defined]
    )
    libelles = [d["libelle"] for d in response.json()]
    assert "Comptabilité" in libelles


@pytest.mark.asyncio
async def test_creer_departement_libelle_existant_409(
    client: AsyncClient, superviseur: Agent, departement: Departement
) -> None:
    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/departements",
        json={"libelle": departement.libelle},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_desactiver_departement_avec_agents_actifs_409(
    client: AsyncClient,
    db: AsyncSession,
    superviseur: Agent,
    departement: Departement,
) -> None:
    """CA-11 : département avec agents actifs → HTTP 409 explicite."""
    # Rattacher le superviseur au département
    superviseur.departement_id = departement.id
    await db.flush()

    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.delete(
        f"/api/departements/{departement.id}",
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 409
    assert "agent" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_desactiver_departement_sans_agents_succes(
    client: AsyncClient, db: AsyncSession, superviseur: Agent
) -> None:
    """Département sans agents actifs → désactivation OK."""
    nouveau_dep = Departement(tenant_id=superviseur.tenant_id, libelle="Vide")
    db.add(nouveau_dep)
    await db.flush()

    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.delete(
        f"/api/departements/{nouveau_dep.id}",
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 200
    assert response.json()["actif"] is False

    # Vérifier en base
    result = await db.execute(select(Departement).where(Departement.id == nouveau_dep.id))
    assert result.scalar_one().actif is False


@pytest.mark.asyncio
async def test_agent_standard_ne_peut_pas_creer_departement_403(
    client: AsyncClient, agent_standard: Agent
) -> None:
    token = await pytest.jeton_pour(client, agent_standard.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/departements",
        json={"libelle": "Tentative"},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_agent_standard_peut_lister_departements(
    client: AsyncClient, agent_standard: Agent
) -> None:
    """Lecture des départements ouverte à tous les agents connectés."""
    token = await pytest.jeton_pour(client, agent_standard.login)  # type: ignore[attr-defined]
    response = await client.get(
        "/api/departements", headers=pytest.en_tete_auth(token)  # type: ignore[attr-defined]
    )
    assert response.status_code == 200
