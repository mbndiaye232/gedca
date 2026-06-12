"""Configuration centralisée via variables d'environnement.

Chargée une fois au démarrage. `get_settings()` est mémoïsé.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Réglages d'application chargés depuis l'environnement."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Déploiement ---
    deployment_mode: Literal["saas", "onprem"] = "onprem"
    log_level: str = "INFO"

    # --- Base ---
    database_url: str

    @field_validator("database_url")
    @classmethod
    def _normaliser_database_url(cls, v: str) -> str:
        """Force le driver asyncpg.

        Render (et la plupart des hébergeurs) exposent l'URL en
        `postgres://` ou `postgresql://`. SQLAlchemy async + Alembic
        exigent `postgresql+asyncpg://`. On réécrit le schéma pour que
        l'URL fournie par le dashboard soit utilisable telle quelle.
        """
        for prefixe in ("postgresql+asyncpg://", "postgresql+psycopg://"):
            if v.startswith(prefixe):
                return v
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://") :]
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://") :]
        return v

    # --- Redis / Celery ---
    redis_url: str = "redis://redis:6379/0"
    celery_worker_concurrency: int = 2
    imap_poll_interval_min: int = 15
    imap_staging_ttl_days: int = 30

    # --- Sécurité ---
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    allowed_origins: str = "http://localhost:5173"
    master_key: str = Field(..., description="Clé maître AES-256 en base64 (32 octets)")

    # --- Stockage ---
    # 'local' : disque (dev / on-prem). 'r2' : Cloudflare R2 (SaaS cloud) —
    # indispensable sur Render dont le disque est éphémère.
    storage_backend: Literal["local", "r2"] = "local"
    storage_root: str = "/app/storage"
    quarantine_path: str = "/app/storage/quarantaine"
    worker_temp_dir: str = "/app/storage/tmp"
    max_upload_size_mb: int = 100

    # --- Cloudflare R2 (requis si storage_backend = 'r2') ---
    # R2 est compatible S3 ; on s'y connecte via boto3. L'endpoint peut être
    # fourni directement, sinon il est dérivé de l'Account ID.
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str | None = None
    r2_endpoint: str | None = None

    # --- Watcher ---
    watcher_root: str = "/app/storage/inbox"
    watcher_enabled: bool = False
    watcher_force_polling: bool = False

    # --- IA ---
    ai_provider: Literal["anthropic", "ollama"] = "ollama"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    voyage_api_key: str | None = None
    embedding_model_cloud: str = "voyage-3"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    embedding_model_local: str = "intfloat/multilingual-e5-large"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Origines CORS sous forme de liste exploitable par FastAPI."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def r2_endpoint_url(self) -> str | None:
        """URL de l'endpoint R2 — fournie explicitement ou dérivée de l'Account ID."""
        if self.r2_endpoint:
            return self.r2_endpoint
        if self.r2_account_id:
            return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"
        return None


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance unique de Settings."""
    return Settings()  # type: ignore[call-arg]
