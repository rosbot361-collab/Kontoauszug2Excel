"""
Auto-Cleanup-Service für alte Dateien und Jobs
Löscht automatisch abgelaufene Jobs nach 15 Minuten (DSGVO)
"""
import shutil
from pathlib import Path
import logging
from threading import Thread
import time

from api.config import UPLOAD_DIR
from api.services.database import get_expired_jobs, delete_job

logger = logging.getLogger(__name__)


def cleanup_expired_jobs():
    """
    Löscht abgelaufene Jobs und deren Dateien.
    Wird automatisch alle 5 Minuten ausgeführt.
    """
    logger.info("🧹 Running cleanup job...")

    expired_job_ids = get_expired_jobs()

    for job_id in expired_job_ids:
        try:
            # Lösche Job-Dateien
            job_dir = UPLOAD_DIR / job_id
            if job_dir.exists():
                shutil.rmtree(job_dir)
                logger.info(f"Deleted files for job {job_id}")

            # Lösche Job aus DB
            delete_job(job_id)

        except Exception as e:
            logger.error(f"Error cleaning up job {job_id}: {e}")

    if expired_job_ids:
        logger.info(f"✅ Cleaned up {len(expired_job_ids)} expired jobs")
    else:
        logger.info("No expired jobs to clean up")


def cleanup_scheduler():
    """
    Background-Thread der alle 5 Minuten Cleanup ausführt.
    """
    while True:
        try:
            cleanup_expired_jobs()
        except Exception as e:
            logger.error(f"Error in cleanup scheduler: {e}")

        # Warte 5 Minuten
        time.sleep(300)


def start_cleanup_scheduler():
    """
    Startet den Cleanup-Scheduler als Background-Thread.
    """
    thread = Thread(target=cleanup_scheduler, daemon=True)
    thread.start()
    logger.info("🕐 Cleanup scheduler started (runs every 5 minutes)")


def delete_job_files(job_id: str):
    """
    Löscht alle Dateien eines Jobs sofort (z.B. auf User-Request).
    """
    job_dir = UPLOAD_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir)
        logger.info(f"Deleted files for job {job_id}")

    delete_job(job_id)
