# 🌊 FloodCast — Live Flood Forecast Dashboard

Forecasting flood patterns from rainfall and InfoWorks ICM simulation data.

An automated live flood forecasting web application and API platform that monitors hourly CSV simulation outputs from InfoWorks ICM, ingests the data into a database, exposes JSON API endpoints for external plugin extraction, and displays live forecasts on an interactive dashboard.

**Location:** Kuching, Sarawak, Malaysia

---

## 🏗️ Architecture

```
InfoWorks ICM Live → CSV exports → data/exports → File Watcher / Ingestion
                                                   ↓
                              SQL Server (production) or SQLite (local)
                                                   ↓
                                FastAPI REST API (/api/v1)
                                                   ↓
                                  Vue.js Dashboard
```

ICM Live hands forecast and alert exports to the watched export directory. The
backend parses and persists them, and the dashboard reads the resulting data
through the REST API; it does not connect directly to the database. SQLite is
the zero-configuration default, while SQL Server can be selected with
`DATABASE_URL`.

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** (for backend)
- **Node.js 22+** (for frontend)

### 1. Start the Backend (FastAPI)

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 2. Start the Frontend (Vue.js)

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:5173`.

### 3. Ingest Data

Drop your ICM CSV files into the `data/exports/` directory:

- `Node_Flood Forecast*.csv` — Time-series forecast data
- `*Alert definition list*.csv` — Alert/warning definitions

The file watcher will automatically detect and ingest new files.

For a deployed ICM Live workflow, configure its scheduled/export process to
write `Node_Flood Forecast*.csv` and `*Alert definition list*.csv` into the
backend's `DATA_DIR` (defaults to `data/exports/`). The watcher ingests new or
changed files; the Vue dashboard receives updates through the API polling
endpoints.

### Use SQL Server

1. Install Microsoft ODBC Driver 18 for SQL Server on the backend host and
   install the Python dependencies with `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` in the repository root and set `DATABASE_URL`
   to an async SQLAlchemy URL, for example:

   ```env
   DATABASE_URL=mssql+aioodbc://USER:PASSWORD@SERVER:1433/DATABASE?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
   ```

3. Ensure the SQL Server database exists and the configured account can create
   and modify the application's tables. Start the backend as usual; startup
   initializes the schema and `/health` reports database connectivity.

URL-encode reserved characters in usernames or passwords. Keep `.env` out of
source control and use a secrets manager for deployed credentials.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/api/v1/nodes` | List all monitoring nodes with current status |
| `GET` | `/api/v1/node-forecast?node_id=Drain_53` | Get water level forecast for a node |
| `GET` | `/api/v1/node-forecast/latest?lat=1.4908&lon=110.2738` | Nearest node spatial forecast |
| `GET` | `/api/v1/alerts/active` | Currently active alerts |
| `GET` | `/api/v1/alerts/history` | Alert history with filtering |
| `GET` | `/api/v1/dashboard/summary` | Dashboard summary statistics |
| `GET` | `/docs` | Interactive Swagger API docs |
| `GET` | `/health` | System health check |

---

## 📁 Project Structure

```
Flood Live Data Website/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration & constants
│   │   ├── database.py          # Async SQLite engine
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic response schemas
│   │   ├── routers/
│   │   │   ├── forecasts.py     # Node & forecast endpoints
│   │   │   ├── alerts.py        # Alert endpoints
│   │   │   └── dashboard.py     # Dashboard summary
│   │   └── services/
│   │       ├── csv_ingester.py  # CSV parsing & upsert
│   │       └── file_watcher.py  # Watchdog + APScheduler
│   ├── schema.sql               # Reference SQL schema
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FloodMap.vue     # Leaflet GIS map
│   │   │   ├── HydrographChart.vue # ECharts time-series
│   │   │   ├── AlertFeed.vue    # Alert notification panel
│   │   │   └── StatsBar.vue     # Summary statistics
│   │   ├── views/
│   │   │   └── DashboardView.vue
│   │   ├── composables/
│   │   │   └── useApi.ts        # API client
│   │   ├── assets/main.css      # Design system
│   │   ├── App.vue              # Root layout
│   │   └── main.ts              # Entry point
│   └── vite.config.ts
├── data/
│   ├── exports/                 # Drop ICM CSVs and Shapefiles (.shp, .dbf, .shx) here
│   └── geojson/                 # Converted WGS84 GeoJSON layers for Leaflet
└── README.md
```

---

## 🌊 2D Flood Inundation & Time-Lapse Player

FloodCast automatically ingests InfoWorks ICM 2D flood inundation Shapefiles:

1. **Auto-Reprojection**: Reads incoming `.shp`, `.dbf`, `.shx` files, automatically detects local coordinate systems (such as Sarawak RSO `EPSG:29873` or UTM), and reprojects them into standard WGS84 (`EPSG:4326`) GeoJSON.
2. **REST Endpoints**:
   - `GET /api/v1/contours/timesteps` — Returns chronological list of simulation frames (e.g. `["1000", "1100", ..., "1800"]`).
   - `GET /api/v1/contours/{timestamp}` — Returns GeoJSON `FeatureCollection` with depth and elevation properties.
3. **Interactive Simulation Player**:
   - Play/pause 1-second interval animation through simulation hours.
   - Interactive time slider scrubber with direct frame jumps.
   - Depth-graded styling (`<0.5m` cyan, `0.5-1.2m` blue, `>1.2m` dark blue) with interactive telemetry popups on click/hover.

---

## ⚙️ Configuration

Edit `backend/app/config.py` to customize:

- **Node metadata** (GIS coordinates, names)
- **Warning/alert thresholds** (default: 2.0m / 3.0m)
- **Watch interval** (default: 3600 seconds)
- **CORS origins** (frontend dev server URLs)

---

## Database Options

SQLite is the default for local development. Set `DATABASE_URL` to an async
SQLAlchemy URL to use another supported database. SQL Server uses the
`mssql+aioodbc` dialect and requires its Microsoft ODBC driver; PostgreSQL
requires `postgresql+asyncpg` and the `asyncpg` package.

---

## 📄 License

MIT
