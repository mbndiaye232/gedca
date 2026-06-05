"""Test critique CA-06 : isolation tenant.

Un agent du tenant A ne doit JAMAIS pouvoir lire ou modifier des données
d'un autre tenant — quel que soit son rôle.
"""

from __future__ import annotations

import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Tenant
from app.services.password import hacher_mot_de_passe


@pytest.mark.asyncio
async def test_superviseur_ne_voit_pas_agents_autre_tenant(
    client: AsyncClient,
    db: AsyncSession,
    superviseur: Agent,
    autre_tenant: Tenant,
) -> None:
    """CA-06 : superviseur du tenant A ne voit pas les agents du tenant B."""
    # Créer un agent dans l'autre tenant
    agent_b = Agent(
        tenant_id=autre_tenant.id,
        login="agent_tenant_b",
        password_hash=hacher_mot_de_passe("Password123!"),
        auth_provider="local",
        nom="B",
        prenom="Agent",
        email="b@tenant-b.local",
        role_id=2,
        actif=True,
    )
    db.add(agent_b)
    await db.flush()

    token_sup = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.get(
        "/api/agents", headers=pytest.en_tete_auth(token_sup)  # type: ignore[attr-defined]
    )
    assert response.status_code == 200
    logins = [a["login"] for a in response.json()]
    assert agent_b.login not in logins
    # Seuls les agents du tenant courant sont visibles
    for entry in response.json():
        assert entry["login"] != agent_b.login


@pytest.mark.asyncio
async def test_acces_agent_autre_tenant_par_id_404(
    client: AsyncClient,
    db: AsyncSession,
    superviseur: Agent,
    autre_tenant: Tenant,
) -> None:
    """Accès direct à un agent d'un autre tenant par ID → 404 (pas de fuite d'existence)."""
    agent_b = Agent(
        tenant_id=autre_tenant.id,
        login=f"agentb-{secrets.token_hex(4)}",
        password_hash=hacher_mot_de_passe("Password123!"),
        auth_provider="local",
        nom="B",
        prenom="Agent",
        role_id=2,
        actif=True,
    )
    db.add(agent_b)
    await db.flush()

    token_sup = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.get(
        f"/api/agents/{agent_b.id}", headers=pytest.en_tete_auth(token_sup)  # type: ignore[attr-defined]
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_maj_agent_autre_tenant_404(
    client: AsyncClient,
    db: AsyncSession,
    superviseur: Agent,
    autre_tenant: Tenant,
) -> None:
    """Modification d'un agent d'un autre tenant → 404."""
    agent_b = Agent(
        tenant_id=autre_tenant.id,
        login=f"victim-{secrets.token_hex(4)}",
        password_hash=hacher_mot_de_passe("Password123!"),
        auth_provider="local",
        nom="B",
        prenom="Victim",
        role_id=2,
        actif=True,
    )
    db.add(agent_b)
    await db.flush()

    token_sup = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.put(
        f"/api/agents/{agent_b.id}",
        json={"nom": "Compromis"},
        headers=pytest.en_tete_auth(token_sup),  # type: ignore[attr-defined]
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_structure_du_tenant_courant_uniquement(
    client: AsyncClient, superviseur: Agent, autre_tenant: Tenant
) -> None:
    """GET /api/structure retourne le tenant courant, jamais un autre."""
    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.get(
        "/api/structure", headers=pytest.en_tete_auth(token)  # type: ignore[attr-defined]
    )
    assert response.status_code == 200
    assert response.json()["id"] == superviseur.tenant_id
    assert response.json()["id"] != autre_tenant.id
