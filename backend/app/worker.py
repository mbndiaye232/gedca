"""Application Celery pour les tâches asynchrones (OCR, chiffrement, embeddings, IMAP, mails)."""

from __future__ import annotations

import asyncio

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "gedca",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.worker",  # registered tasks live here for now
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
# Lancement : celery -A app.worker beat --loglevel=info
celery_app.conf.beat_schedule = {
    "alertes-retard-quotidiennes": {
        "task": "app.worker.task_alertes_retard_quotidiennes",
        "schedule": crontab(hour=7, minute=0),
    },
}


@celery_app.task(name="app.worker.task_alertes_retard_quotidiennes")
def task_alertes_retard_quotidiennes() -> dict[str, int]:
    """Wrapper Celery pour la fonction async `envoyer_alertes_quotidiennes`.

    Import tardif pour éviter le coût du graphe SQLAlchemy au boot du
    worker quand la tâche n'est pas appelée.
    """
    from app.tasks.alertes_retard import envoyer_alertes_quotidiennes

    return asyncio.run(envoyer_alertes_quotidiennes())
