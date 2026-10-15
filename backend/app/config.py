"""
Application configuration and constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root
load_dotenv(BASE_DIR / ".env")
DATA_DIR = os.getenv("DATA_DIR", str(BASE_DIR / "data" / "exports"))
GEOJSON_DIR = os.getenv("GEOJSON_DIR", str(BASE_DIR / "data" / "geojson"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'backend' / 'flood_data.db'}")

# ─── File Watcher ────────────────────────────────────────────────────────────
WATCH_INTERVAL_SECONDS = 60 * 60  # Hourly fallback scan
FILE_STABILITY_WAIT = 2  # Seconds to wait for file to stop being written

# ─── File Patterns ───────────────────────────────────────────────────────────
FORECAST_CSV_PATTERN = "Node_Flood Forecast"  # Filename must contain this
ALERT_CSV_PATTERN = "Alert definition list"    # Filename must contain this
SHAPEFILE_PATTERN = "FloodContours"            # Legacy single pattern
SHAPEFILE_PATTERNS = ["FloodContours", "DTM_"] # Filename prefixes for ICM 2D contours

# ─── GIS / Projections ───────────────────────────────────────────────────────
# Default local Sarawak CRS used when shapefile .prj is omitted or undefined
DEFAULT_LOCAL_CRS = "EPSG:29874"  # Timbalai 1948 / RSO Sarawak LSD (m)
TARGET_CRS = "EPSG:4326"         # WGS84 for GeoJSON / Web Mercator maps

# ─── Alert / Warning / Danger Thresholds (meters) ─────────────────────────────────────
# These can be overridden per-node in the future
DEFAULT_ALERT_THRESHOLD = 2.0
DEFAULT_WARNING_THRESHOLD = 3.0
DEFAULT_DANGER_THRESHOLD = 4.0

# ─── Node Metadata (Kuching, Sarawak drain network) ─────────────────────────
# GIS coordinates for known monitoring nodes
NODE_METADATA = {
    "Drain_46": {
        "name": "Drain 46 - Sungai Padungan",
        "latitude": 1.5535,
        "longitude": 110.3485,
        "node_type": "drain",
        "alert_threshold": DEFAULT_ALERT_THRESHOLD,
        "warning_threshold": DEFAULT_WARNING_THRESHOLD,
        "danger_threshold": DEFAULT_DANGER_THRESHOLD,
    },
    "Drain_53": {
        "name": "Drain 53 - Sungai Sarawak",
        "latitude": 1.5590,
        "longitude": 110.3440,
        "node_type": "drain",
        "alert_threshold": DEFAULT_ALERT_THRESHOLD,
        "warning_threshold": DEFAULT_WARNING_THRESHOLD,
        "danger_threshold": DEFAULT_DANGER_THRESHOLD,
    },
}

# ─── API ─────────────────────────────────────────────────────────────────────
API_V1_PREFIX = "/api/v1"
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
