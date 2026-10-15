"""
CSV ingestion service — parses ICM forecast and alert CSVs, upserts into database.

Handles:
  - Node_Flood Forecast*.csv → WaterLevelReading rows (wide → long pivot)
  - *Alert definition list*.csv → AlertDefinition rows
"""

import hashlib
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure backend root is on sys.path if script is executed directly
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import NODE_METADATA
from app.database import AsyncSessionLocal
from app.models import WaterLevelReading, AlertDefinition, FileIngestLog, Node

logger = logging.getLogger("flood.ingester")


def compute_file_hash(filepath: str) -> str:
    """Compute MD5 hash of a file for change detection."""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _parse_datetime_flexible(value) -> datetime | None:
    """Try multiple datetime formats common in ICM exports."""
    if pd.isna(value) or value is None:
        return None

    if isinstance(value, datetime):
        return value

    value_str = str(value).strip()
    if not value_str:
        return None

    # Common ICM date formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %I:%M %p",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %I:%M:%S %p",
        "%d-%m-%Y %I:%M %p",
        "%Y-%m-%d %I:%M:%S %p",
        "%Y-%m-%d %I:%M %p",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value_str, fmt)
        except ValueError:
            continue

    # Last resort: pandas parser
    try:
        return pd.to_datetime(value_str, dayfirst=True).to_pydatetime()
    except Exception:
        logger.warning(f"Could not parse datetime: {value_str!r}")
        return None


async def _has_file_changed(filepath: str, file_hash: str) -> bool:
    """Check whether the latest successful ingestion matches the current file."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FileIngestLog.file_hash)
            .where(FileIngestLog.filepath == filepath)
            .where(FileIngestLog.status == "success")
            .order_by(FileIngestLog.processed_at.desc(), FileIngestLog.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none() != file_hash


async def _log_ingestion(
    filepath: str,
    file_hash: str,
    file_type: str,
    rows_processed: int,
    status: str = "success",
    error_message: str | None = None,
):
    """Record file ingestion in the log table."""
    async with AsyncSessionLocal() as session:
        log_entry = FileIngestLog(
            filepath=filepath,
            file_hash=file_hash,
            file_type=file_type,
            rows_processed=rows_processed,
            status=status,
            error_message=error_message,
        )
        session.add(log_entry)
        await session.commit()


async def _ensure_node_exists(session: AsyncSession, node_id: str):
    """Create a node record if it doesn't exist (auto-discovers new drain columns)."""
    result = await session.execute(select(Node).where(Node.id == node_id))
    if result.scalar_one_or_none() is None:
        meta = NODE_METADATA.get(node_id, {})
        node = Node(
            id=node_id,
            name=meta.get("name", node_id.replace("_", " ")),
            latitude=meta.get("latitude", 1.5535),  # Default Kuching coords
            longitude=meta.get("longitude", 110.3485),
            node_type=meta.get("node_type", "drain"),
            alert_threshold=meta.get("alert_threshold", 2.0),
            warning_threshold=meta.get("warning_threshold", 3.0),
            danger_threshold=meta.get("danger_threshold", 4.0),
        )
        session.add(node)
        await session.flush()


async def ingest_forecast_csv(filepath: str) -> dict:
    """
    Parse a Node_Flood Forecast CSV file and upsert water level readings.

    Expected CSV format (wide):
        Time, Seconds, Drain_46, Drain_53, [... more drain columns]

    Pivots wide format into normalized rows: one row per (node_id, timestamp).
    Returns ingestion stats.
    """
    filepath = str(filepath)
    file_hash = compute_file_hash(filepath)
    filename = Path(filepath).name

    # Check if already processed
    if not await _has_file_changed(filepath, file_hash):
        logger.info(f"Skipping unchanged file: {filename}")
        return {"status": "skipped", "reason": "unchanged", "file": filename}

    logger.info(f"Ingesting forecast CSV: {filename}")
    stats = {"file": filename, "rows_inserted": 0, "rows_updated": 0, "errors": 0}

    try:
        # Read CSV with flexible encoding
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(filepath, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"Could not decode {filename} with any supported encoding")

        # Normalize column names: strip whitespace
        df.columns = [col.strip() for col in df.columns]

        # Identify the time and seconds columns
        time_col = None
        seconds_col = None
        for col in df.columns:
            if col.lower() == "time":
                time_col = col
            elif col.lower() == "seconds":
                seconds_col = col

        if time_col is None:
            raise ValueError(f"No 'Time' column found in {filename}. Columns: {list(df.columns)}")

        # Identify drain/node columns (everything that's not Time or Seconds)
        node_columns = [
            col for col in df.columns
            if col not in (time_col, seconds_col) and col.strip() != ""
        ]

        if not node_columns:
            raise ValueError(f"No node data columns found in {filename}")

        logger.info(f"Found {len(node_columns)} node columns: {node_columns}")

        async with AsyncSessionLocal() as session:
            # Ensure all nodes exist
            for node_id in node_columns:
                await _ensure_node_exists(session, node_id)

            # Delete existing readings from this source file for clean re-import
            await session.execute(
                delete(WaterLevelReading).where(WaterLevelReading.source_file == filename)
            )

            # Process each row
            batch = []
            for _, row in df.iterrows():
                timestamp = _parse_datetime_flexible(row.get(time_col))
                seconds = float(row.get(seconds_col, 0)) if seconds_col and pd.notna(row.get(seconds_col)) else None

                if timestamp is None:
                    stats["errors"] += 1
                    continue

                for node_id in node_columns:
                    value = row.get(node_id)
                    if pd.isna(value):
                        continue

                    try:
                        water_level = float(value)
                    except (ValueError, TypeError):
                        stats["errors"] += 1
                        continue

                    batch.append(WaterLevelReading(
                        node_id=node_id,
                        timestamp=timestamp,
                        seconds=seconds,
                        water_level=water_level,
                        source_file=filename,
                    ))
                    stats["rows_inserted"] += 1

            # Bulk insert
            if batch:
                session.add_all(batch)

            await session.commit()

        stats["status"] = "success"
        await _log_ingestion(filepath, file_hash, "forecast", stats["rows_inserted"])
        logger.info(f"Ingested {stats['rows_inserted']} readings from {filename}")

    except Exception as e:
        stats["status"] = "error"
        stats["error"] = str(e)
        logger.error(f"Error ingesting {filename}: {e}", exc_info=True)
        await _log_ingestion(filepath, file_hash, "forecast", 0, "error", str(e))

    return stats


async def ingest_alert_csv(filepath: str) -> dict:
    """
    Parse an Alert definition list CSV and upsert alert records.

    Expected CSV columns:
        Alert definition ID, Onset time, End time, Priority,
        Target ID, Target type, Category, Peak value, Peak value units, Peak time

    Upserts by alert_definition_id.
    Returns ingestion stats.
    """
    filepath = str(filepath)
    file_hash = compute_file_hash(filepath)
    filename = Path(filepath).name

    if not await _has_file_changed(filepath, file_hash):
        logger.info(f"Skipping unchanged file: {filename}")
        return {"status": "skipped", "reason": "unchanged", "file": filename}

    logger.info(f"Ingesting alert CSV: {filename}")
    stats = {"file": filename, "rows_upserted": 0, "errors": 0}

    try:
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(filepath, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"Could not decode {filename} with any supported encoding")

        df.columns = [col.strip() for col in df.columns]

        # Map expected columns (case-insensitive, flexible)
        col_map = {}
        for col in df.columns:
            lower = col.lower()
            if "alert" in lower and "id" in lower:
                col_map["alert_definition_id"] = col
            elif "onset" in lower:
                col_map["onset_time"] = col
            elif "end" in lower and "time" in lower:
                col_map["end_time"] = col
            elif "priority" in lower:
                col_map["priority"] = col
            elif "target" in lower and "id" in lower:
                col_map["target_id"] = col
            elif "target" in lower and "type" in lower:
                col_map["target_type"] = col
            elif "category" in lower:
                col_map["category"] = col
            elif "peak" in lower and "unit" in lower:
                col_map["peak_value_units"] = col
            elif "peak" in lower and "time" in lower:
                col_map["peak_time"] = col
            elif "peak" in lower and "value" in lower:
                col_map["peak_value"] = col

        if "alert_definition_id" not in col_map:
            raise ValueError(f"No 'Alert definition ID' column found. Columns: {list(df.columns)}")

        async with AsyncSessionLocal() as session:
            # Clear existing alerts from this source for clean re-import
            await session.execute(
                delete(AlertDefinition).where(AlertDefinition.source_file == filename)
            )

            batch = []
            for _, row in df.iterrows():
                alert_id = str(row.get(col_map.get("alert_definition_id", ""), "")).strip()
                if not alert_id or alert_id == "nan":
                    stats["errors"] += 1
                    continue

                # Parse peak_value
                peak_val = row.get(col_map.get("peak_value", ""), None)
                try:
                    peak_val = float(peak_val) if pd.notna(peak_val) else None
                except (ValueError, TypeError):
                    peak_val = None

                alert = AlertDefinition(
                    alert_definition_id=alert_id,
                    onset_time=_parse_datetime_flexible(row.get(col_map.get("onset_time", ""))),
                    end_time=_parse_datetime_flexible(row.get(col_map.get("end_time", ""))),
                    priority=str(row.get(col_map.get("priority", ""), "")).strip() or None,
                    target_id=str(row.get(col_map.get("target_id", ""), "")).strip() or None,
                    target_type=str(row.get(col_map.get("target_type", ""), "")).strip() or None,
                    category=str(row.get(col_map.get("category", ""), "")).strip() or None,
                    peak_value=peak_val,
                    peak_value_units=str(row.get(col_map.get("peak_value_units", ""), "")).strip() or None,
                    peak_time=_parse_datetime_flexible(row.get(col_map.get("peak_time", ""))),
                    source_file=filename,
                )
                batch.append(alert)
                stats["rows_upserted"] += 1

            if batch:
                session.add_all(batch)

            await session.commit()

        stats["status"] = "success"
        await _log_ingestion(filepath, file_hash, "alert", stats["rows_upserted"])
        logger.info(f"Ingested {stats['rows_upserted']} alerts from {filename}")

    except Exception as e:
        stats["status"] = "error"
        stats["error"] = str(e)
        logger.error(f"Error ingesting {filename}: {e}", exc_info=True)
        await _log_ingestion(filepath, file_hash, "alert", 0, "error", str(e))

    return stats


if __name__ == "__main__":
    import asyncio
    from app.database import init_db
    from app.config import DATA_DIR, FORECAST_CSV_PATTERN, ALERT_CSV_PATTERN

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")

    async def main():
        print("Initializing database...")
        await init_db()

        target_file = sys.argv[1] if len(sys.argv) > 1 else None
        if target_file:
            path = Path(target_file)
            if not path.exists():
                print(f"Error: File not found: {path}")
                return
            if FORECAST_CSV_PATTERN.lower() in path.name.lower():
                res = await ingest_forecast_csv(str(path))
            else:
                res = await ingest_alert_csv(str(path))
            print(f"Result: {res}")
        else:
            print(f"Scanning directory: {DATA_DIR}")
            p = Path(DATA_DIR)
            if not p.exists():
                print(f"Directory does not exist: {p}")
                return
            files = list(p.glob("*.csv"))
            print(f"Found {len(files)} CSV files to ingest.")
            for f in files:
                if FORECAST_CSV_PATTERN.lower() in f.name.lower():
                    res = await ingest_forecast_csv(str(f))
                elif ALERT_CSV_PATTERN.lower() in f.name.lower():
                    res = await ingest_alert_csv(str(f))
                else:
                    print(f"Skipping unrecognized CSV: {f.name}")
                    continue
                print(f"  {f.name} -> {res}")

    asyncio.run(main())
