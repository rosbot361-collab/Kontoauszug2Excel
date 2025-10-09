"""
Celery-Tasks für PDF-Verarbeitung
"""
import logging
from pathlib import Path
from typing import Dict, Any

from api.services.celery_app import celery_app
from api.services.database import update_job, get_job
from api.models.job import JobStatus
from api.config import UPLOAD_DIR
from core.dispatcher import get_parser
from core.exporter import export_to_excel

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="api.services.tasks.process_pdf")
def process_pdf_task(self, job_id: str, bank: str = "auto") -> Dict[str, Any]:
    """
    Celery-Task zum Verarbeiten eines PDFs.

    Args:
        job_id: UUID des Jobs
        bank: Bank-Name (oder "auto" für Auto-Detection)

    Returns:
        Dict mit Ergebnis-Informationen
    """
    logger.info(f"Starting PDF processing for job {job_id}")

    try:
        # Update Status auf PROCESSING
        update_job(job_id, JobStatus.PROCESSING)

        # Dateipfade
        job_dir = UPLOAD_DIR / job_id
        input_pdf = job_dir / "input.pdf"
        output_excel = job_dir / "output.xlsx"

        if not input_pdf.exists():
            raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

        # Bank-Detection falls "auto"
        detected_bank = bank
        if bank == "auto":
            detected_bank = detect_bank(input_pdf)
            logger.info(f"Auto-detected bank: {detected_bank}")

        # Parser holen
        try:
            parser = get_parser(detected_bank)
        except ValueError as e:
            raise ValueError(f"Unsupported bank: {detected_bank}")

        # PDF parsen
        logger.info(f"Parsing PDF with {detected_bank} parser...")
        transactions = parser.parse(str(input_pdf))

        if not transactions:
            raise ValueError("Keine Transaktionen gefunden im PDF")

        # Excel exportieren
        logger.info(f"Exporting {len(transactions)} transactions to Excel...")
        export_to_excel(transactions, str(output_excel))

        # Input-PDF löschen (Datenschutz)
        input_pdf.unlink()
        logger.info("Input PDF deleted for privacy")

        # Job als COMPLETED markieren
        update_job(job_id, JobStatus.COMPLETED, bank=detected_bank)

        logger.info(f"✅ Job {job_id} completed successfully")

        return {
            "job_id": job_id,
            "status": "completed",
            "transactions_count": len(transactions),
            "bank": detected_bank
        }

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        update_job(job_id, JobStatus.FAILED, error_message=str(e))

        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        }


def detect_bank(pdf_path: Path) -> str:
    """
    Erkennt automatisch die Bank anhand des PDFs.
    Einfache Heuristik: Testet alle Parser und nimmt den mit den meisten Transaktionen.

    Args:
        pdf_path: Pfad zum PDF

    Returns:
        Bank-Name (z.B. "sparkasse", "ing")
    """
    from parsers.sparkasse_parser import SparkasseParser
    from parsers.ing_parser import INGParser
    from parsers.db_parser import DBParser

    parsers = {
        "sparkasse": SparkasseParser(),
        "ing": INGParser(),
        "deutsche_bank": DBParser()
    }

    best_bank = None
    max_transactions = 0

    for bank_name, parser in parsers.items():
        try:
            transactions = parser.parse(str(pdf_path))
            if len(transactions) > max_transactions:
                max_transactions = len(transactions)
                best_bank = bank_name
        except Exception as e:
            logger.debug(f"Parser {bank_name} failed: {e}")

    if not best_bank:
        raise ValueError("Konnte Bank nicht automatisch erkennen")

    return best_bank
