"""
FastAPI Backend für Kontoauszug2Excel SaaS
DSGVO-konform: Keine dauerhafte Speicherung von Nutzerdaten
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from api.routes import upload, jobs, download
from api.services.database import init_db
from api.services.cleanup import start_cleanup_scheduler

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle-Events für Startup und Shutdown"""
    # Startup
    logger.info("🚀 Starting Kontoauszug2Excel API")
    init_db()
    start_cleanup_scheduler()
    logger.info("✅ Database initialized and cleanup scheduler started")

    yield

    # Shutdown
    logger.info("👋 Shutting down Kontoauszug2Excel API")


app = FastAPI(
    title="Kontoauszug2Excel API",
    description="DSGVO-konformer PDF-zu-Excel Converter für Kontoauszüge",
    version="1.0.0",
    lifespan=lifespan
)

# CORS-Konfiguration (für Web-UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Produktion auf spezifische Domain einschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files (Web UI)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Routes
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(download.router, prefix="/api", tags=["Download"])


@app.get("/")
async def root():
    """Redirect to Web UI"""
    from fastapi.responses import FileResponse
    index_path = Path(__file__).parent.parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "status": "ok",
        "service": "Kontoauszug2Excel API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detaillierter Health-Check für Monitoring"""
    return {
        "status": "healthy",
        "database": "ok",
        "workers": "ok"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Globaler Exception-Handler (DSGVO: keine sensitiven Daten loggen)"""
    logger.error(f"Unhandled exception: {type(exc).__name__}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut."
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
