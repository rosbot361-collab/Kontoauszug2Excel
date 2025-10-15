"""
Konfiguration für das Backend
"""
import os
from pathlib import Path

# Base-Pfade
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
TEMP_DIR = BASE_DIR / "temp"
DATA_DIR = BASE_DIR / "data"  # NEU: Für Datenbank

# Erstelle Verzeichnisse falls nicht vorhanden
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)  # NEU: Datenbank-Verzeichnis

# Datei-Einstellungen
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf"}

# Job-Einstellungen
JOB_RETENTION_MINUTES = 15  # Nach 15 Minuten automatisch löschen
MAX_JOBS_PER_IP_PER_HOUR = 999999  # Rate-Limiting (DISABLED FOR TESTING)

# Datenbank
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "jobs.db"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

# Celery (Redis)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# DSGVO-Einstellungen
LOG_IP_ADDRESSES = False  # IPs nicht loggen (DSGVO)
ANONYMIZE_LOGS = True  # Logs anonymisieren
