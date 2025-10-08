# 🔧 Troubleshooting Guide

Häufige Probleme und Lösungen für Kontoauszug2Excel

---

## 🗄️ Datenbank-Probleme

### Problem: "unable to open database file"

**Symptome:**
```
sqlite3.OperationalError: unable to open database file
Container startet nicht oder crasht
```

**Ursachen:**
1. Datenbank-Verzeichnis nicht beschreibbar
2. Docker-Volume nicht korrekt gemountet
3. Fehlende Permissions

**Lösungen:**

#### Lösung 1: Verzeichnis-Permissions prüfen (Lokal)
```bash
# Verzeichnis erstellen
mkdir -p data

# Schreibrechte geben
chmod 777 data

# Testen
touch data/.test && rm data/.test
```

#### Lösung 2: Docker-Volumes neu erstellen
```bash
# Alle Container und Volumes stoppen und löschen
docker-compose down -v

# Verzeichnisse lokal erstellen
mkdir -p data uploads temp

# Neu bauen und starten
docker-compose build --no-cache
docker-compose up -d
```

#### Lösung 3: Manuelle DB-Pfad-Konfiguration
```bash
# .env Datei erstellen
echo "DATABASE_PATH=/tmp/jobs.db" > .env

# Docker neu starten
docker-compose down
docker-compose up -d
```

#### Lösung 4: Logs prüfen
```bash
# API-Logs anschauen
docker-compose logs api | grep -i database

# Sollte zeigen:
# ✅ Database initialized
# Falls Fallback: WARNING: Falling back to /tmp/jobs.db
```

---

## 🐳 Docker-Probleme

### Problem: "Cannot connect to Docker daemon"

**Lösung:**
```bash
# Docker Desktop starten
# Windows: Start → Docker Desktop
# Mac: Spotlight → Docker

# Warten bis Icon grün ist
# Testen:
docker ps
```

### Problem: "Port 8000 already in use"

**Lösung:**
```bash
# Prozess finden
netstat -ano | findstr :8000   # Windows
lsof -i :8000                  # Linux/Mac

# Prozess beenden
taskkill /PID <PID> /F         # Windows
kill -9 <PID>                  # Linux/Mac

# Oder anderen Port nutzen:
# In docker-compose.yml:
# ports: ["8001:8000"]
```

### Problem: "Container unhealthy"

**Lösung:**
```bash
# Container-Status prüfen
docker-compose ps

# Logs anschauen
docker-compose logs api

# Healthcheck manuell testen
docker-compose exec api curl http://localhost:8000/health

# Container neu starten
docker-compose restart api
```

---

## 🔴 Redis-Probleme

### Problem: "Connection refused: redis:6379"

**Lösung (Lokal ohne Docker):**
```bash
# Redis installieren
# Windows: https://github.com/tporadowski/redis/releases
# Mac: brew install redis
# Linux: apt install redis-server

# Redis starten
redis-server

# Testen:
redis-cli ping   # Sollte "PONG" zurückgeben
```

**Lösung (Docker):**
```bash
# Redis-Container prüfen
docker-compose logs redis

# Redis neu starten
docker-compose restart redis

# Manuell testen
docker-compose exec redis redis-cli ping
```

---

## 🔄 Celery-Probleme

### Problem: "Received unregistered task of type 'tasks.process_pdf'"

**Symptome:**
```
ERROR: Received unregistered task of type 'tasks.process_pdf'
The message has been ignored and discarded.
```

**Ursache:** Celery findet die Task nicht (Import-Problem)

**Lösung:**
```bash
# Container neu bauen (Fix ist bereits im Code)
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Logs prüfen - sollte jetzt funktionieren
docker-compose logs celery_worker | grep -i "registered tasks"
```

**Technisch:** Task-Name muss vollqualifiziert sein: `api.services.tasks.process_pdf`

---

### Problem: "PDF wird nicht verarbeitet"

**Symptome:**
- Upload funktioniert
- Status bleibt auf "pending"
- Kein Download-Button erscheint

**Lösung:**
```bash
# Celery-Logs prüfen
docker-compose logs celery_worker

# Häufige Fehler:
# 1. Redis-Verbindung fehlgeschlagen
# 2. Parser-Fehler (ungültiges PDF)
# 3. Import-Fehler (fehlende Dependencies)
# 4. Task nicht registriert (siehe oben)

# Celery neu starten
docker-compose restart celery_worker
```

### Problem: "ModuleNotFoundError: No module named..."

**Lösung:**
```bash
# Container neu bauen (Dependencies installieren)
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 📄 PDF-Parsing-Probleme

### Problem: "Keine Transaktionen gefunden im PDF"

**Mögliche Ursachen:**
1. PDF ist gescannt (Bild statt Text) → OCR nötig
2. Bank wird nicht unterstützt
3. PDF-Format hat sich geändert

**Lösung:**
```bash
# 1. Prüfen ob PDF Text enthält
pdftotext kontoauszug.pdf -   # Sollte Text ausgeben

# 2. Unterstützte Banken prüfen
# Aktuell: Sparkasse, ING

# 3. Debug-Modus aktivieren (Lokal):
python main.py --bank sparkasse --input test.pdf --output out.xlsx --debug
```

### Problem: "Transaktionen unvollständig"

**Lösung:**
```bash
# Parser-Logik anpassen in parsers/<bank>_parser.py
# Oder: Issue auf GitHub erstellen mit Beispiel-PDF (anonymisiert!)
```

---

## 🌐 Web-UI-Probleme

### Problem: "Seite lädt nicht (localhost:8000)"

**Lösung:**
```bash
# 1. API läuft?
docker-compose ps api   # Sollte "Up (healthy)" zeigen

# 2. Port richtig?
curl http://localhost:8000/health

# 3. Browser-Cache leeren
# Chrome: Strg+Shift+Delete
# Firefox: Strg+Shift+Delete

# 4. Anderen Browser testen
```

### Problem: "Upload hängt / lädt ewig"

**Lösung:**
```bash
# 1. Browser-Console öffnen (F12)
# Fehler anschauen

# 2. Datei zu groß?
# Max: 10 MB

# 3. Rate-Limit erreicht?
# Max: 5 Uploads/Stunde/IP
curl http://localhost:8000/api/upload/limits

# 4. Backend-Logs prüfen
docker-compose logs -f api
```

---

## 💾 Datenbank-Wartung

### Problem: "Datenbank zu groß"

**Lösung:**
```bash
# Datenbank manuell cleanen
docker-compose exec api python -c "
from api.services.cleanup import cleanup_expired_jobs
cleanup_expired_jobs()
"

# Oder: Datenbank löschen (ACHTUNG: Alle Jobs weg!)
rm data/jobs.db
docker-compose restart api
```

### Problem: "Datenbank korrupt"

**Lösung:**
```bash
# Backup erstellen
cp data/jobs.db data/jobs.db.backup

# Datenbank neu erstellen
rm data/jobs.db
docker-compose restart api
```

---

## 🔍 Allgemeine Debug-Tipps

### Alle Logs anschauen

```bash
# Alle Services
docker-compose logs -f

# Nur API
docker-compose logs -f api

# Nur Celery
docker-compose logs -f celery_worker

# Nur Redis
docker-compose logs -f redis

# Letzte 100 Zeilen
docker-compose logs --tail=100
```

### Container-Status prüfen

```bash
# Status aller Container
docker-compose ps

# Ressourcen-Nutzung
docker stats

# In Container einloggen
docker-compose exec api bash
docker-compose exec celery_worker bash
```

### Netzwerk prüfen

```bash
# Kann API Redis erreichen?
docker-compose exec api ping redis

# Kann API nach außen?
docker-compose exec api curl https://google.com
```

---

## 🆘 Noch Probleme?

### Schritt 1: Komplett-Reset

```bash
# WARNUNG: Löscht alle Daten!
docker-compose down -v
rm -rf uploads/* temp/* data/*
docker-compose build --no-cache
docker-compose up -d
```

### Schritt 2: Issue auf GitHub

```
https://github.com/rosbot361-collab/Kontoauszug2Excel/issues
```

**Bitte angeben:**
- Betriebssystem (Windows/Mac/Linux)
- Docker-Version (`docker --version`)
- Fehlermeldung (vollständig)
- Logs (`docker-compose logs`)
- Schritte zur Reproduktion

---

## ✅ Checkliste: Gesundes System

```bash
# Alle grün?
✓ docker-compose ps        # Alle "Up (healthy)"
✓ curl localhost:8000      # HTML wird geladen
✓ curl localhost:8000/health  # {"status":"healthy"}
✓ ls -la data/             # jobs.db existiert
✓ docker-compose logs redis   # Keine Errors
✓ docker-compose logs api     # "Database initialized"
```

---

**💡 Tipp:** Die meisten Probleme lösen sich durch `docker-compose down -v && docker-compose up -d --build`
