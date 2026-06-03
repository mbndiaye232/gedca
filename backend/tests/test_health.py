"""Test minimal de l'endpoint de santé."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Variables minimales pour que Settings se charge en environnement de test
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret-for-tests-only")
os.environ.setdefault("MASTER_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")

from app.main import app  # noqa: E402


@pytest.mark.asyncio
async def test_health_repond_ok() -> None:
    """L'endpoint /api/health renvoie statut ok et la version."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["statut"] == "ok"
    assert "version" in body
    assert body["mode"] in {"saas", "onprem"}
