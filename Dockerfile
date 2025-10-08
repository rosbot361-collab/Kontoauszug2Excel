# Dockerfile für FastAPI Backend
FROM python:3.11-slim

# Arbeitsverzeichnis
WORKDIR /app

# System-Dependencies für pdfplumber und Healthcheck
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python-Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungs-Code
COPY . .

# Verzeichnisse erstellen mit korrekten Permissions
RUN mkdir -p /app/uploads /app/temp /app/data && \
    chmod 777 /app/uploads /app/temp /app/data

# Port freigeben
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Start-Command (wird von docker-compose überschrieben)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
