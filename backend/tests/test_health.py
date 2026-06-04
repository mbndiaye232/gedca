"""Test minimal de l'endpoint de santé."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_repond_ok(client: AsyncClient) -> None:
    """L'endpoint /api/health renvoie statut ok et la version."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["statut"] == "ok"
    assert "version" in body
    assert body["mode"] in {"saas", "onprem"}
