#!/bin/bash
# Start-Script für Kontoauszug2Excel

set -e

echo "🚀 Starting Kontoauszug2Excel..."

# Verzeichnisse erstellen
echo "📁 Creating directories..."
mkdir -p uploads temp data

# Schreibrechte prüfen
if ! touch data/.test 2>/dev/null; then
    echo "❌ data/ Verzeichnis nicht beschreibbar!"
    echo "Bitte Berechtigungen prüfen: chmod 777 data/"
    exit 1
fi
rm -f data/.test

# Prüfen ob Redis läuft
if ! pgrep -x "redis-server" > /dev/null; then
    echo "❌ Redis ist nicht gestartet!"
    echo "Bitte starte Redis mit: redis-server"
    exit 1
fi

# Virtual Environment aktivieren
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

source venv/bin/activate || source venv/Scripts/activate

# Dependencies installieren
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Celery Worker starten (im Hintergrund)
echo "🔄 Starting Celery worker..."
celery -A api.services.celery_app worker --loglevel=info --concurrency=2 > celery.log 2>&1 &
CELERY_PID=$!

# FastAPI starten
echo "🌐 Starting FastAPI server..."
echo "✅ App running at http://localhost:8000"
echo "Press Ctrl+C to stop..."

python -m api.main

# Cleanup beim Beenden
trap "echo '👋 Stopping services...' && kill $CELERY_PID" EXIT
