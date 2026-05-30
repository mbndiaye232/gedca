"""Application Celery pour les tâches asynchrones (OCR, chiffrement, embeddings, IMAP, mails)."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "gedca",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        # TODO: ajouter au fur et à mesure
        # "app.tasks.ingestion",
        # "app.tasks.alerts",
        # "app.tasks.imap",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Cron des jobs planifiés (Celery Beat)
celery_app.conf.beat_schedule = {
    # Alertes retard quotidiennes — chaque matin à 7h UTC
    # "alertes-retard-quotidiennes": {
    #     "task": "app.tasks.alerts.envoyer_alertes_retard",
    #     "schedule": crontab(hour=7, minute=0),
    # },
    # Polling IMAP toutes les 10 minutes
    # "polling-imap": {
    #     "task": "app.tasks.imap.recuperer_pieces_jointes",
    #     "schedule": crontab(minute="*/10"),
    # },
}
