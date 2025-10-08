@echo off
REM Start-Script für Windows

echo Starting Kontoauszug2Excel...

REM Verzeichnisse erstellen
echo Creating directories...
if not exist "uploads" mkdir uploads
if not exist "temp" mkdir temp
if not exist "data" mkdir data

REM Virtual Environment aktivieren
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

REM Dependencies installieren
echo Installing dependencies...
pip install -q -r requirements.txt

REM Redis-Check
echo.
echo WICHTIG: Redis muss separat gestartet sein!
echo Download: https://github.com/tporadowski/redis/releases
echo.

REM Celery Worker starten
echo Starting Celery worker...
start /B celery -A api.services.celery_app worker --loglevel=info --concurrency=2

REM FastAPI starten
echo Starting FastAPI server...
echo.
echo App running at http://localhost:8000
echo Press Ctrl+C to stop...
echo.

python -m api.main

pause
