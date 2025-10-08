"""
Job-Status-Endpoint
"""
import logging
from fastapi import APIRouter, HTTPException
from api.models.job import JobResponse
from api.services.database import get_job

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """
    Holt den Status eines Jobs.

    Args:
        job_id: UUID des Jobs

    Returns:
        JobResponse mit aktuellem Status
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    return job
