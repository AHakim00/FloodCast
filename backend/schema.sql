-- ============================================================================
-- Flood Live Data — Reference SQL Schema
-- ============================================================================
-- This is a SQLite reference schema, not a SQL Server migration script.
-- SQLAlchemy ORM creates tables for the configured database at application startup.
--
-- OPTIONAL POSTGRESQL / TIMESCALEDB NOTES:
-- 1. Set DATABASE_URL to: postgresql+asyncpg://user:pass@host/dbname
-- 2. Install asyncpg.
-- 3. For TimescaleDB, convert water_level_readings to a hypertable:
--    SELECT create_hypertable('water_level_readings', 'timestamp');
-- 4. Add PostGIS extension for spatial queries:
--    CREATE EXTENSION postgis;
--    ALTER TABLE nodes ADD COLUMN geom geometry(Point, 4326);
-- ============================================================================

-- Monitoring nodes with GIS coordinates
CREATE TABLE IF NOT EXISTS nodes (
    id              VARCHAR(64)     PRIMARY KEY,
    name            VARCHAR(256)    NOT NULL,
    latitude        DOUBLE PRECISION NOT NULL,
    longitude       DOUBLE PRECISION NOT NULL,
    node_type       VARCHAR(64)     DEFAULT 'drain',
    alert_threshold   DOUBLE PRECISION DEFAULT 2.0,
    warning_threshold DOUBLE PRECISION DEFAULT 3.0,
    danger_threshold  DOUBLE PRECISION DEFAULT 4.0,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- Time-series water level readings from ICM forecast simulations
CREATE TABLE IF NOT EXISTS water_level_readings (
    id              INTEGER         PRIMARY KEY AUTOINCREMENT,
    node_id         VARCHAR(64)     NOT NULL REFERENCES nodes(id),
    timestamp       TIMESTAMP       NOT NULL,
    seconds         DOUBLE PRECISION,
    water_level     DOUBLE PRECISION NOT NULL,
    source_file     VARCHAR(512),
    ingested_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- Composite index for efficient time-series queries
CREATE INDEX IF NOT EXISTS idx_readings_node_time
    ON water_level_readings (node_id, timestamp);

-- Index for source file lookups (used during re-ingestion)
CREATE INDEX IF NOT EXISTS idx_readings_source
    ON water_level_readings (source_file);

-- Alert/warning/Danger definitions from ICM Live data exports
CREATE TABLE IF NOT EXISTS alert_definitions (
    id                      INTEGER         PRIMARY KEY AUTOINCREMENT,
    alert_definition_id     VARCHAR(128)    NOT NULL UNIQUE,
    onset_time              TIMESTAMP,
    end_time                TIMESTAMP,
    priority                VARCHAR(64),
    target_id               VARCHAR(64),
    target_type             VARCHAR(64),
    category                VARCHAR(128),
    peak_value              DOUBLE PRECISION,
    peak_value_units        VARCHAR(32),
    peak_time               TIMESTAMP,
    source_file             VARCHAR(512),
    ingested_at             TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- Index for target-based alert lookups
CREATE INDEX IF NOT EXISTS idx_alerts_target
    ON alert_definitions (target_id);

-- Index for time-based active alert queries
CREATE INDEX IF NOT EXISTS idx_alerts_time
    ON alert_definitions (onset_time, end_time);

-- File ingestion log to prevent re-processing unchanged files
CREATE TABLE IF NOT EXISTS file_ingest_log (
    id              INTEGER         PRIMARY KEY AUTOINCREMENT,
    filepath        VARCHAR(1024)   NOT NULL,
    file_hash       VARCHAR(64)     NOT NULL,
    file_type       VARCHAR(32)     NOT NULL,
    rows_processed  INTEGER         DEFAULT 0,
    status          VARCHAR(32)     DEFAULT 'success',
    error_message   TEXT,
    processed_at    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
