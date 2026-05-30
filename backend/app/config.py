"""Configuration centralisée via variables d'environnement.

Chargée une fois au démarrage. `get_settings()` est mémoïsé.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Réglages d'application chargés depuis l'environnement."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Déploiement ---
    deployment_mode: Literal["saas", "onprem"] = "onprem"
    log_level: str = "INFO"

    # --- Base ---
    database_url: str

    # --- Redis / Celery ---
    redis_url: str = "redis://redis:6379/0"

    # --- Sécurité ---
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    master_key: str = Field(..., description="Clé maître AES-256 en base64 (32 octets)")

    # --- Stockage ---
    storage_path: str = "/app/storage"
    quarantine_path: str = "/app/storage/quarantaine"
    watch_folder: str = "/app/storage/inbox"

    # --- IA ---
    ai_provider: Literal["anthropic", "ollama"] = "ollama"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    voyage_api_key: str | None = None
    embedding_model_cloud: str = "voyage-multilingual-2"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    embedding_model_local: str = "intfloat/multilingual-e5-large"


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance unique de Settings."""
    return Settings()  # type: ignore[call-arg]
