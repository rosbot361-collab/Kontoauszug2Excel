"""
Job-Modell für die Datenbank
Speichert nur Metadaten, keine Transaktionsdaten (DSGVO)
"""
from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class JobStatus(str, Enum):
    """Job-Status-Enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreate(BaseModel):
    """Schema für Job-Erstellung"""
    bank: Optional[str] = "auto"
    output_format: str = "xlsx"


class JobResponse(BaseModel):
    """Schema für Job-Antwort"""
    job_id: str
    status: JobStatus
    bank: Optional[str] = None
    output_format: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobUpdate(BaseModel):
    """Schema für Job-Updates"""
    status: Optional[JobStatus] = None
    bank: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
