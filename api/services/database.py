"""
Datenbank-Service für Job-Management
SQLite für MVP, später PostgreSQL
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import logging
import uuid

from api.config import DATABASE_PATH, JOB_RETENTION_MINUTES
from api.models.job import JobStatus, JobCreate, JobResponse

logger = logging.getLogger(__name__)

DB_PATH = Path(DATABASE_PATH)


def get_connection():
    """Erstellt eine Datenbankverbindung mit Fallback"""
    global DB_PATH

    # Stelle sicher, dass Verzeichnis existiert
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Cannot create directory {DB_PATH.parent}: {e}")

    # Versuche Verbindung
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        # Test write access
        conn.execute("SELECT 1").fetchone()
        return conn
    except sqlite3.OperationalError as e:
        logger.error(f"Cannot open database at {DB_PATH}: {e}")

        # Fallback auf /tmp (immer beschreibbar)
        fallback_path = Path("/tmp/jobs.db")
        logger.warning(f"Falling back to {fallback_path}")
        DB_PATH = fallback_path

        conn = sqlite3.connect(str(fallback_path))
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    """Initialisiert die Datenbank"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            bank TEXT,
            output_format TEXT NOT NULL DEFAULT 'xlsx',
            created_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            expires_at TIMESTAMP,
            error_message TEXT,
            ip_hash TEXT
        )
    """)

    # Index für schnellere Abfragen
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)
    """)

    conn.commit()
    conn.close()
    logger.info("✅ Database initialized")


def create_job(job_data: JobCreate, ip_hash: Optional[str] = None) -> JobResponse:
    """Erstellt einen neuen Job"""
    job_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(minutes=JOB_RETENTION_MINUTES)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jobs (id, status, bank, output_format, created_at, expires_at, ip_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id,
        JobStatus.PENDING.value,
        job_data.bank,
        job_data.output_format,
        created_at,
        expires_at,
        ip_hash
    ))

    conn.commit()
    conn.close()

    logger.info(f"Created job {job_id}")

    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        bank=job_data.bank,
        output_format=job_data.output_format,
        created_at=created_at,
        expires_at=expires_at
    )


def get_job(job_id: str) -> Optional[JobResponse]:
    """Holt einen Job anhand der ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return JobResponse(
        job_id=row["id"],
        status=JobStatus(row["status"]),
        bank=row["bank"],
        output_format=row["output_format"],
        created_at=datetime.fromisoformat(row["created_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
        error_message=row["error_message"],
        download_url=f"/api/download/{row['id']}" if row["status"] == JobStatus.COMPLETED.value else None
    )


def update_job(job_id: str, status: JobStatus, error_message: Optional[str] = None, bank: Optional[str] = None):
    """Updated einen Job-Status"""
    conn = get_connection()
    cursor = conn.cursor()

    completed_at = datetime.utcnow() if status in [JobStatus.COMPLETED, JobStatus.FAILED] else None

    if bank:
        cursor.execute("""
            UPDATE jobs
            SET status = ?, error_message = ?, completed_at = ?, bank = ?
            WHERE id = ?
        """, (status.value, error_message, completed_at, bank, job_id))
    else:
        cursor.execute("""
            UPDATE jobs
            SET status = ?, error_message = ?, completed_at = ?
            WHERE id = ?
        """, (status.value, error_message, completed_at, job_id))

    conn.commit()
    conn.close()

    logger.info(f"Updated job {job_id} to status {status.value}")


def get_expired_jobs() -> List[str]:
    """Holt alle abgelaufenen Jobs"""
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow()
    cursor.execute("SELECT id FROM jobs WHERE expires_at < ?", (now,))
    rows = cursor.fetchall()
    conn.close()

    return [row["id"] for row in rows]


def delete_job(job_id: str):
    """Löscht einen Job aus der Datenbank"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

    logger.info(f"Deleted job {job_id} from database")


def count_recent_jobs_by_ip(ip_hash: str, hours: int = 1) -> int:
    """Zählt Jobs einer IP der letzten X Stunden (Rate-Limiting)"""
    conn = get_connection()
    cursor = conn.cursor()

    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM jobs
        WHERE ip_hash = ? AND created_at > ?
    """, (ip_hash, cutoff_time))

    result = cursor.fetchone()
    conn.close()

    return result["count"] if result else 0
