"""Tests d'authentification (CA-01 à CA-04, CA-09, CA-10 du PRD-01)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, AuditLog


@pytest.mark.asyncio
async def test_login_credentials_valides_retourne_jwt(
    client: AsyncClient, superviseur: Agent
) -> None:
    """CA-01 : login valide → 200 + JWT + agent + rôle correct."""
    response = await client.post(
        "/api/auth/login",
        json={"login": superviseur.login, "mot_de_passe": "Password123!"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "access_token" in body and body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["agent"]["login"] == superviseur.login
    assert body["agent"]["role"] == "superviseur"
    assert body["agent"]["tenant_id"] == superviseur.tenant_id


@pytest.mark.asyncio
async def test_login_mauvais_mot_de_passe_401_message_generique(
    client: AsyncClient, superviseur: Agent
) -> None:
    """CA-02 : mauvais mdp → 401 avec message générique."""
    response = await client.post(
        "/api/auth/login",
        json={"login": superviseur.login, "mot_de_passe": "WRONG"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Identifiants invalides"


@pytest.mark.asyncio
async def test_login_inconnu_meme_message_generique(client: AsyncClient) -> None:
    """RG-1 : un login qui n'existe pas reçoit le même message."""
    response = await client.post(
        "/api/auth/login",
        json={"login": "inconnu", "mot_de_passe": "WRONG"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Identifiants invalides"


@pytest.mark.asyncio
async def test_agent_inactif_ne_peut_pas_se_connecter(
    client: AsyncClient, db: AsyncSession, superviseur: Agent
) -> None:
    """CA-03 : agent désactivé → 401."""
    superviseur.actif = False
    await db.flush()
    response = await client.post(
        "/api/auth/login",
        json={"login": superviseur.login, "mot_de_passe": "Password123!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_route_protegee_sans_token_401(client: AsyncClient) -> None:
    """CA-04 : appel d'une route protégée sans Authorization → 401."""
    response = await client.get("/api/agents/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_route_protegee_token_invalide_401(client: AsyncClient) -> None:
    """Token bidon → 401."""
    response = await client.get(
        "/api/agents/me",
        headers={"Authorization": "Bearer not.a.valid.jwt"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_succes_inscrit_audit_log(
    client: AsyncClient, db: AsyncSession, superviseur: Agent
) -> None:
    """CA-09 : login réussi → ligne audit_log action=login avec agent_id, tenant_id, ip."""
    response = await client.post(
        "/api/auth/login",
        json={"login": superviseur.login, "mot_de_passe": "Password123!"},
    )
    assert response.status_code == 200

    result = await db.execute(
        select(AuditLog).where(
            AuditLog.action == "login",
            AuditLog.agent_id == superviseur.id,
        )
    )
    log = result.scalar_one()
    assert log.tenant_id == superviseur.tenant_id
    assert log.entite == "agents"
    assert log.entite_id == superviseur.id


@pytest.mark.asyncio
async def test_login_echec_inscrit_audit_log(
    client: AsyncClient, db: AsyncSession, superviseur: Agent
) -> None:
    """CA-10 : échec d'authentification → ligne audit_log action=login_echec."""
    await client.post(
        "/api/auth/login",
        json={"login": superviseur.login, "mot_de_passe": "WRONG"},
    )

    result = await db.execute(
        select(AuditLog).where(AuditLog.action == "login_echec")
    )
    log = result.scalar_one()
    assert log.payload.get("login") == superviseur.login
    assert log.payload.get("raison") == "mot_de_passe_invalide"


@pytest.mark.asyncio
async def test_login_met_a_jour_derniere_connexion(
    client: AsyncClient, db: AsyncSession, superviseur: Agent
) -> None:
    """RG-5 : derniere_connexion mise à jour après login réussi."""
    assert superviseur.derniere_connexion is None
    await client.post(
        "/api/auth/login",
        json={"login": superviseur.login, "mot_de_passe": "Password123!"},
    )
    await db.refresh(superviseur)
    assert superviseur.derniere_connexion is not None


@pytest.mark.asyncio
async def test_logout_inscrit_audit_log(
    client: AsyncClient, db: AsyncSession, superviseur: Agent
) -> None:
    """Déconnexion → entry audit_log action=logout."""
    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/auth/logout", headers=pytest.en_tete_auth(token)  # type: ignore[attr-defined]
    )
    assert response.status_code == 204

    result = await db.execute(
        select(AuditLog).where(
            AuditLog.action == "logout", AuditLog.agent_id == superviseur.id
        )
    )
    assert result.scalar_one() is not None
