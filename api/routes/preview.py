"""
Preview and Update Endpoints
Ermöglicht Vorschau und Bearbeitung von konvertierten Daten
"""
import logging
import json
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from pathlib import Path

from api.services.database import get_job, update_job

logger = logging.getLogger(__name__)
router = APIRouter()


class Transaction(BaseModel):
    """Transaction data model"""
    date: str = ""
    description: str = ""
    reference: str = ""
    debit: str = ""
    credit: str = ""
    balance: str = ""


class PreviewResponse(BaseModel):
    """Response model for preview data"""
    job_id: str
    bank: str
    output_format: str
    transactions: List[Transaction]


class UpdateRequest(BaseModel):
    """Request model for updating transactions"""
    transactions: List[Transaction]


@router.get("/preview/{job_id}", response_model=PreviewResponse)
async def get_preview(job_id: str):
    """
    Holt die Vorschau der konvertierten Daten.

    Args:
        job_id: UUID des Jobs

    Returns:
        PreviewResponse mit allen Transaktionsdaten
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    # Try to find result file even if job status is not completed yet
    from api.config import UPLOAD_DIR
    job_dir = UPLOAD_DIR / job_id
    result_path = None

    logger.info(f"Looking for result file in: {job_dir}")

    # Look for output file
    if (job_dir / "output.xlsx").exists():
        result_path = job_dir / "output.xlsx"
        logger.info(f"Found output.xlsx")
    elif (job_dir / "output.csv").exists():
        result_path = job_dir / "output.csv"
        logger.info(f"Found output.csv")
    elif job.get('result_path'):
        result_path = Path(job['result_path'])
        logger.info(f"Using result_path from job: {result_path}")

    if not result_path or not result_path.exists():
        logger.error(f"Result file not found. Job dir contents: {list(job_dir.iterdir()) if job_dir.exists() else 'dir not found'}")
        raise HTTPException(status_code=404, detail="Ergebnisdatei nicht gefunden")

    try:
        # Lese Excel/CSV Datei
        if job['output_format'] == 'xlsx':
            df = pd.read_excel(result_path)
        else:
            df = pd.read_csv(result_path)

        # Konvertiere zu JSON-kompatiblem Format
        transactions = []
        for _, row in df.iterrows():
            transaction = Transaction(
                date=str(row.get('Date', row.get('Datum', ''))),
                description=str(row.get('Description', row.get('Beschreibung', ''))),
                reference=str(row.get('Reference', row.get('Referenz', ''))),
                debit=str(row.get('Debit', row.get('Soll', ''))),
                credit=str(row.get('Credit', row.get('Haben', ''))),
                balance=str(row.get('Balance', row.get('Saldo', '')))
            )
            transactions.append(transaction)

        return PreviewResponse(
            job_id=job_id,
            bank=job['bank'],
            output_format=job['output_format'],
            transactions=transactions
        )

    except Exception as e:
        logger.error(f"Error loading preview for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Laden der Vorschau")


@router.post("/update/{job_id}")
async def update_preview(job_id: str, request: UpdateRequest):
    """
    Aktualisiert die Transaktionsdaten nach der Bearbeitung.

    Args:
        job_id: UUID des Jobs
        request: UpdateRequest mit bearbeiteten Transaktionen

    Returns:
        Job-Informationen
    """
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    if job['status'] != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Job ist noch nicht abgeschlossen (Status: {job['status']})"
        )

    result_path = Path(job['result_path'])

    try:
        # Konvertiere Transaktionen zu DataFrame
        data = []
        for trans in request.transactions:
            data.append({
                'Datum': trans.date,
                'Beschreibung': trans.description,
                'Referenz': trans.reference,
                'Soll': trans.debit,
                'Haben': trans.credit,
                'Saldo': trans.balance
            })

        df = pd.DataFrame(data)

        # Speichere aktualisierte Datei
        if job['output_format'] == 'xlsx':
            df.to_excel(result_path, index=False, engine='openpyxl')
        else:
            df.to_csv(result_path, index=False)

        logger.info(f"Updated {len(request.transactions)} transactions for job {job_id}")

        return {
            "job_id": job_id,
            "status": "completed",
            "message": f"{len(request.transactions)} Transaktionen aktualisiert",
            "bank": job['bank'],
            "output_format": job['output_format']
        }

    except Exception as e:
        logger.error(f"Error updating job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Aktualisieren der Daten")
