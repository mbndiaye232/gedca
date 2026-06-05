"""Fixtures pytest partagées.

Stratégie : on s'appuie sur le PostgreSQL réel (extensions vector / pg_trgm
ne sont pas disponibles en SQLite). Chaque test tourne dans une transaction
ouverte au début et roll-backée à la fin → isolation totale sans truncate.

Pré-requis :
- `alembic upgrade head` exécuté une fois sur la base de test
- variable d'env TEST_DATABASE_URL pointant sur cette base
"""

from __future__ import annotations

import asyncio
import base64
import os
import secrets
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# --- Variables d'env de test ------------------------------------------------
# Doivent être posées AVANT l'import de app.* (qui charge les settings).

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://gedca:gedca@localhost:5432/gedca_test",
    ),
)
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod-" + secrets.token_hex(8))
os.environ.setdefault(
    "MASTER_KEY", base64.b64encode(secrets.token_bytes(32)).decode()
)
os.environ.setdefault("ALLOWED_ORIGINS", "http://testserver")

from app.api.deps import get_db  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Agent, Categorie, Departement, Role, Tenant  # noqa: E402
from app.services.password import hacher_mot_de_passe  # noqa: E402


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Boucle asyncio partagée pour toute la session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def _engine():
    """Engine SQLAlchemy de session.

    NullPool : pas de réutilisation de connexion entre tests, évite les
    problèmes de event-loop sur asyncpg quand pytest-asyncio recrée la boucle.
    """
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(
        get_settings().database_url,
        future=True,
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()


_TABLES_A_TRUNCATE = (
    # Ordre : tables avec FK d'abord (CASCADE gère le reste)
    "audit_log",
    "documents_sous_dossiers",
    "document_versions",
    "documents",
    "categories",
    "thematiques",
    "types_document",
    "correspondants",
    "sous_dossiers",
    "dossiers_classeurs",
    "boites",
    "rayons",
    "locaux_salles",
    "sites",
    "agents",
    "departements",
    "tenants",
)


async def _truncate_tables(engine) -> None:
    """Vide les tables métier (préserve roles et types_correspondant seedés)."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(
            text(f"TRUNCATE {', '.join(_TABLES_A_TRUNCATE)} RESTART IDENTITY CASCADE")
        )


@pytest_asyncio.fixture
async def db(_engine) -> AsyncGenerator[AsyncSession, None]:
    """Session DB normale. Truncate des tables métier après chaque test."""
    factory = async_sessionmaker(_engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
    await _truncate_tables(_engine)


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP qui partage la session DB du test (donc rollback à la fin)."""

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


# --- Helpers de seed --------------------------------------------------------


@pytest_asyncio.fixture
async def tenant(db: AsyncSession) -> Tenant:
    """Crée un tenant de test."""
    t = Tenant(
        code=f"test-{secrets.token_hex(4)}",
        raison_sociale="Tenant Test",
        email="test@example.com",
        ai_provider="anthropic",
    )
    db.add(t)
    await db.flush()
    return t


@pytest_asyncio.fixture
async def autre_tenant(db: AsyncSession) -> Tenant:
    """Deuxième tenant pour tester l'isolation."""
    t = Tenant(
        code=f"autre-{secrets.token_hex(4)}",
        raison_sociale="Autre Tenant",
        email="autre@example.com",
        ai_provider="anthropic",
    )
    db.add(t)
    await db.flush()
    return t


@pytest_asyncio.fixture
async def departement(db: AsyncSession, tenant: Tenant) -> Departement:
    dep = Departement(tenant_id=tenant.id, libelle="Direction test")
    db.add(dep)
    await db.flush()
    return dep


@pytest_asyncio.fixture
async def categorie(db: AsyncSession, tenant: Tenant) -> Categorie:
    """Catégorie de test (obligatoire pour uploader un document)."""
    c = Categorie(tenant_id=tenant.id, libelle=f"cat-{secrets.token_hex(3)}")
    db.add(c)
    await db.flush()
    return c


@pytest.fixture(autouse=True)
def storage_dir(tmp_path, monkeypatch):
    """Isole le stockage des fichiers chiffrés par test (tempdir auto-cleanup).

    autouse=True pour s'appliquer à tous les tests sans dépendance explicite.
    Vide le cache des Settings pour que le nouveau STORAGE_ROOT soit pris en compte.
    """
    racine = tmp_path / "storage"
    racine.mkdir()
    monkeypatch.setenv("STORAGE_ROOT", str(racine))
    get_settings.cache_clear()
    yield racine
    get_settings.cache_clear()


def _build_agent(
    *, tenant: Tenant, role_code: str, login: str, mot_de_passe: str = "Password123!",
) -> Agent:
    return Agent(
        tenant_id=tenant.id,
        login=login,
        password_hash=hacher_mot_de_passe(mot_de_passe),
        auth_provider="local",
        nom="Test",
        prenom=login.capitalize(),
        email=f"{login}@test.local",
        role_id=_role_id_par_code(role_code),
        actif=True,
    )


_ROLE_IDS: dict[str, int] = {"superviseur": 1, "archiviste": 2, "agent_standard": 3}


def _role_id_par_code(code: str) -> int:
    return _ROLE_IDS[code]


@pytest_asyncio.fixture
async def superviseur(db: AsyncSession, tenant: Tenant) -> Agent:
    a = _build_agent(tenant=tenant, role_code="superviseur", login="sup")
    db.add(a)
    await db.flush()
    # Recharger pour avoir la relation role chargée
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    result = await db.execute(select(Agent).options(joinedload(Agent.role)).where(Agent.id == a.id))
    return result.scalar_one()


@pytest_asyncio.fixture
async def archiviste(db: AsyncSession, tenant: Tenant) -> Agent:
    a = _build_agent(tenant=tenant, role_code="archiviste", login="arch")
    db.add(a)
    await db.flush()
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    result = await db.execute(select(Agent).options(joinedload(Agent.role)).where(Agent.id == a.id))
    return result.scalar_one()


@pytest_asyncio.fixture
async def agent_standard(db: AsyncSession, tenant: Tenant) -> Agent:
    a = _build_agent(tenant=tenant, role_code="agent_standard", login="std")
    db.add(a)
    await db.flush()
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    result = await db.execute(select(Agent).options(joinedload(Agent.role)).where(Agent.id == a.id))
    return result.scalar_one()


async def jeton_pour(client: AsyncClient, login: str, mot_de_passe: str = "Password123!") -> str:
    """Récupère un JWT en faisant un login HTTP réel."""
    response = await client.post(
        "/api/auth/login", json={"login": login, "mot_de_passe": mot_de_passe}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def en_tete_auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# Expose en module pour réutilisation dans les tests
pytest.jeton_pour = jeton_pour  # type: ignore[attr-defined]
pytest.en_tete_auth = en_tete_auth  # type: ignore[attr-defined]


# Évite un import inutilisé qui passerait à ruff
_ = Role
_ = Any
