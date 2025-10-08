"""
Upload-Endpoint für PDF-Kontoauszüge
"""
import hashlib
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse

from api.config import UPLOAD_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, MAX_JOBS_PER_IP_PER_HOUR
from api.models.job import JobCreate, JobResponse
from api.services.database import create_job, count_recent_jobs_by_ip
from api.services.tasks import process_pdf_task

logger = logging.getLogger(__name__)
router = APIRouter()


def get_ip_hash(request: Request) -> str:
    """
    Erstellt einen anonymisierten Hash der IP-Adresse.
    DSGVO-konform: Speichert nicht die echte IP.
    """
    client_ip = request.client.host
    return hashlib.sha256(client_ip.encode()).hexdigest()[:16]


@router.post("/upload", response_model=JobResponse)
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    bank: str = Form("auto"),
    output_format: str = Form("xlsx")
):
    """
    Upload-Endpoint für PDF-Kontoauszüge.

    Args:
        file: PDF-Datei
        bank: Bank-Name (sparkasse, ing, auto)
        output_format: Ausgabeformat (xlsx, csv)

    Returns:
        JobResponse mit job_id und Status
    """
    # Rate-Limiting Check
    ip_hash = get_ip_hash(request)
    recent_jobs = count_recent_jobs_by_ip(ip_hash, hours=1)

    if recent_jobs >= MAX_JOBS_PER_IP_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {MAX_JOBS_PER_IP_PER_HOUR} uploads per hour."
        )

    # Datei-Validierung
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Nur PDF-Dateien sind erlaubt"
        )

    # Dateigröße prüfen
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Datei zu groß. Max. {MAX_FILE_SIZE / 1024 / 1024} MB erlaubt."
        )

    # Job erstellen
    job_data = JobCreate(bank=bank, output_format=output_format)
    job = create_job(job_data, ip_hash=ip_hash)

    # Job-Verzeichnis erstellen
    job_dir = UPLOAD_DIR / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # PDF speichern
    input_pdf = job_dir / "input.pdf"
    with open(input_pdf, "wb") as f:
        f.write(file_content)

    logger.info(f"Uploaded PDF for job {job.job_id} ({len(file_content)} bytes)")

    # Celery-Task starten
    process_pdf_task.delay(job.job_id, bank)

    return job


@router.get("/upload/limits")
async def get_upload_limits(request: Request):
    """
    Gibt die aktuellen Rate-Limits für die IP zurück.
    """
    ip_hash = get_ip_hash(request)
    recent_jobs = count_recent_jobs_by_ip(ip_hash, hours=1)

    return {
        "max_uploads_per_hour": MAX_JOBS_PER_IP_PER_HOUR,
        "remaining_uploads": max(0, MAX_JOBS_PER_IP_PER_HOUR - recent_jobs),
        "used_uploads": recent_jobs
    }
