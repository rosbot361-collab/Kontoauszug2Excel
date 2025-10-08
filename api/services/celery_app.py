"""
Celery-App für asynchrone PDF-Verarbeitung
"""
from celery import Celery
from api.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "kontoauszug2excel",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['api.services.tasks']  # Task-Module automatisch laden
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Berlin",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 Minuten max. pro Task
    worker_prefetch_multiplier=1,
)
