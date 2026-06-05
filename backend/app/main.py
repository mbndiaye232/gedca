"""Point d'entrée de l'API FastAPI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_router
from app.config import get_settings
from app.services.crypto import ConfigurationCryptoError, _cle_maitre

logger = logging.getLogger("gedca")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Hook de démarrage / arrêt de l'application."""
    settings = get_settings()
    # Refuser de démarrer si MASTER_KEY absente ou mal formée — règle PRD-02 §5.1 RG-9
    try:
        _cle_maitre()
    except ConfigurationCryptoError as exc:
        logger.error("Configuration cryptographique invalide : %s", exc)
        raise
    logger.info(
        "GEDCA démarré (mode=%s, ai_provider=%s, version=%s)",
        settings.deployment_mode,
        settings.ai_provider,
        __version__,
    )
    yield
    logger.info("GEDCA arrêté.")


app = FastAPI(
    title="GEDCA API",
    version=__version__,
    description=(
        "API GEDCA — Gestion Électronique de Documents, Gestion Électronique de Courriers, "
        "Archivage physique."
    ),
    lifespan=lifespan,
)

# CORS — origines listées dans ALLOWED_ORIGINS (virgule-séparées)
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes versionnées v1 (préfixe /api)
app.include_router(api_router)


@app.get("/api/health", tags=["santé"])
async def health() -> dict[str, str]:
    """Endpoint de santé minimal — permet de vérifier que l'API répond."""
    settings = get_settings()
    return {
        "statut": "ok",
        "version": __version__,
        "mode": settings.deployment_mode,
    }
