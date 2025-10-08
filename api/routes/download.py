"""
Download-Endpoint für verarbeitete Excel-Dateien
"""
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.config import UPLOAD_DIR
from api.services.database import get_job
from api.services.cleanup import delete_job_files
from api.models.job import JobStatus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/download/{job_id}")
async def download_result(job_id: str):
    """
    Download-Endpoint für die verarbeitete Excel-Datei.

    Args:
        job_id: UUID des Jobs

    Returns:
        FileResponse mit Excel-Datei
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job ist noch nicht fertig. Aktueller Status: {job.status.value}"
        )

    # Output-Datei suchen
    job_dir = UPLOAD_DIR / job_id
    output_file = job_dir / f"output.{job.output_format}"

    if not output_file.exists():
        raise HTTPException(status_code=404, detail="Output-Datei nicht gefunden")

    logger.info(f"Downloading result for job {job_id}")

    return FileResponse(
        path=str(output_file),
        filename=f"kontoauszug_{job_id[:8]}.{job.output_format}",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.delete("/download/{job_id}")
async def delete_job_data(job_id: str):
    """
    Löscht einen Job und alle zugehörigen Dateien sofort.
    DSGVO: User kann seine Daten jederzeit löschen.

    Args:
        job_id: UUID des Jobs

    Returns:
        Bestätigung
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    delete_job_files(job_id)

    logger.info(f"User deleted job {job_id}")

    return {"message": "Job und alle Daten erfolgreich gelöscht"}
