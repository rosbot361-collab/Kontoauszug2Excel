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
    headers: List[str]
    transactions: List[Dict[str, Any]]

    class Config:
        # Allow arbitrary types to handle any field names
        extra = 'allow'


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
        request: UpdateRequest mit bearbeiteten Transaktionen und Headers

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

    # Find the output file
    from api.config import UPLOAD_DIR
    job_dir = UPLOAD_DIR / job_id
    output_file = job_dir / f"output.{job['output_format']}"

    if not output_file.exists():
        # Try alternative path
        if job.get('result_path'):
            output_file = Path(job['result_path'])

        if not output_file.exists():
            raise HTTPException(status_code=404, detail="Output-Datei nicht gefunden")

    try:
        logger.info(f"Updating job {job_id} with {len(request.transactions)} transactions")
        logger.info(f"Headers: {request.headers}")
        logger.info(f"Output file path: {output_file}")
        logger.info(f"Sample transaction: {request.transactions[0] if request.transactions else 'No transactions'}")

        # Konvertiere Transaktionen zu DataFrame mit dynamischen Headers
        data = []
        for i, trans in enumerate(request.transactions):
            row = {}
            for header in request.headers:
                # Get value from transaction dict, default to empty string
                value = trans.get(header, '')
                row[header] = str(value) if value is not None else ''
            data.append(row)

            # Log first row for debugging
            if i == 0:
                logger.info(f"First row data: {row}")

        if not data:
            raise ValueError("Keine Transaktionsdaten zum Speichern vorhanden")

        df = pd.DataFrame(data, columns=request.headers)

        logger.info(f"Created DataFrame with shape: {df.shape}")
        logger.info(f"DataFrame columns: {df.columns.tolist()}")
        logger.info(f"DataFrame head:\n{df.head()}")

        # Speichere aktualisierte Datei
        if job['output_format'] == 'xlsx':
            df.to_excel(output_file, index=False, engine='openpyxl')
            logger.info(f"Saved updated Excel file to: {output_file}")
        else:
            df.to_csv(output_file, index=False)
            logger.info(f"Saved updated CSV file to: {output_file}")

        # Verify file was written
        if not output_file.exists():
            raise IOError(f"Datei wurde nicht geschrieben: {output_file}")

        file_size = output_file.stat().st_size
        logger.info(f"File written successfully, size: {file_size} bytes")

        logger.info(f"Successfully updated {len(request.transactions)} transactions for job {job_id}")

        return {
            "job_id": job_id,
            "status": "completed",
            "message": f"{len(request.transactions)} Transaktionen aktualisiert",
            "bank": job['bank'],
            "output_format": job['output_format']
        }

    except ValueError as e:
        logger.error(f"Validation error updating job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:
        logger.error(f"IO error updating job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Fehler beim Schreiben der Datei: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Fehler beim Aktualisieren der Daten: {str(e)}")
