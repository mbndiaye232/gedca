"""Point d'entrée de l'API FastAPI."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Hook de démarrage / arrêt de l'application."""
    settings = get_settings()
    # TODO: initialiser le pool DB, vérifier la connectivité Redis, etc.
    _ = settings.deployment_mode
    yield
    # TODO: cleanup


app = FastAPI(
    title="GEDCA API",
    version=__version__,
    description=(
        "API GEDCA — Gestion Électronique de Documents, Gestion Électronique de Courriers, "
        "Archivage physique."
    ),
    lifespan=lifespan,
)

# CORS — à restreindre en prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["santé"])
async def health() -> dict[str, str]:
    """Endpoint de santé minimal — permet de vérifier que l'API répond."""
    settings = get_settings()
    return {
        "statut": "ok",
        "version": __version__,
        "mode": settings.deployment_mode,
    }
