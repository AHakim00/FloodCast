"""
Flood Live Data â€” FastAPI Application Entry Point.

Initializes the database, starts the file watcher service, and mounts
all API routers. Includes CORS middleware for frontend dev server.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

from app.config import API_V1_PREFIX, CORS_ORIGINS, WATCH_INTERVAL_SECONDS
from app.database import engine, init_db
from app.routers import forecasts, alerts, dashboard, contours, geojson
from app.services.file_watcher import FileWatcherService, scan_directory

# â”€â”€â”€ Logging â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s â”‚ %(name)-20s â”‚ %(levelname)-7s â”‚ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("flood.main")

# â”€â”€â”€ Services â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
watcher_service = FileWatcherService()
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle management."""

    # â”€â”€ Startup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    logger.info("=" * 60)
    logger.info("  FLOOD LIVE DATA â€” Starting up")
    logger.info("=" * 60)

    # Initialize database tables and seed node metadata
    await init_db()
    logger.info("Database initialized.")

    # Start file watcher (watchdog observer)
    loop = asyncio.get_running_loop()
    watcher_service.start(loop)

    # Start APScheduler for periodic directory scan (hourly fallback)
    scheduler.add_job(
        scan_directory,
        "interval",
        seconds=WATCH_INTERVAL_SECONDS,
        id="periodic_scan",
        name="Hourly CSV directory scan",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Periodic scanner scheduled (every {WATCH_INTERVAL_SECONDS}s).")

    # Run an initial scan on startup in background (non-blocking)
    asyncio.create_task(scan_directory())
    logger.info("Initial directory scan scheduled.")

    logger.info("=" * 60)
    logger.info("  FLOOD LIVE DATA â€” Ready")
    logger.info("=" * 60)

    yield  # Application runs here

    # â”€â”€ Shutdown â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    logger.info("Shutting down...")
    scheduler.shutdown(wait=False)
    watcher_service.stop()
    logger.info("Shutdown complete.")


# â”€â”€â”€ FastAPI App â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app = FastAPI(
    title="Flood Live Data API",
    description=(
        "Automated flood forecasting platform. "
        "Monitors ICM simulation CSV outputs and exposes live forecast data "
        "via plugin-friendly REST API endpoints."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# â”€â”€â”€ CORS Middleware â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# â”€â”€â”€ Mount Routers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.include_router(forecasts.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(contours.router)
app.include_router(geojson.router)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "service": "Flood Live Data API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    """Report database connectivity and background service status."""
    database_status = "connected"
    status_code = 200
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"
        status_code = 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if status_code == 200 else "degraded",
            "database": database_status,
            "watcher_running": watcher_service.is_running,
            "scheduler_running": scheduler.running,
        },
    )

