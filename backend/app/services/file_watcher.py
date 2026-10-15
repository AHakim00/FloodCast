from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any

from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver
from watchdog.events import FileSystemEventHandler

from app.config import (
    DATA_DIR,
    FORECAST_CSV_PATTERN,
    ALERT_CSV_PATTERN,
    SHAPEFILE_PATTERN,
    FILE_STABILITY_WAIT,
)
from app.services.csv_ingester import ingest_forecast_csv, ingest_alert_csv
from app.services.gis_converter import (
    convert_shapefile_to_geojson,
    convert_all_shapefiles,
    verify_shapefile_ready,
    is_contour_shapefile,
)

logger = logging.getLogger("flood.watcher")


def _classify_csv(filename: str) -> str | None:
    """Determine if a CSV is a forecast or alert file based on its name."""
    if FORECAST_CSV_PATTERN.lower() in filename.lower():
        return "forecast"
    elif ALERT_CSV_PATTERN.lower() in filename.lower():
        return "alert"
    return None


def _wait_for_stability(filepath: str, timeout: float = FILE_STABILITY_WAIT) -> bool:
    """Wait until file size stabilizes (file finished being written)."""
    try:
        prev_size = -1
        stable_count = 0
        for _ in range(int(timeout * 10) + 10):
            current_size = os.path.getsize(filepath)
            if current_size == prev_size and current_size > 0:
                stable_count += 1
                if stable_count >= 2:
                    return True
            else:
                stable_count = 0
            prev_size = current_size
            time.sleep(0.5)
    except OSError:
        return False
    return False


class ExportDirectoryEventHandler(FileSystemEventHandler):
    """
    Handles filesystem events for both CSV telemetry files and
    InfoWorks ICM flood contour Shapefiles in the watch directory.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self._loop = loop
        self._processing = set()  # Prevent concurrent processing of same file

    def on_created(self, event):
        if event.is_directory:
            return
        self._dispatch(os.fsdecode(event.src_path))

    def on_modified(self, event):
        if event.is_directory:
            return
        self._dispatch(os.fsdecode(event.src_path))

    def _dispatch(self, filepath: str):
        lower = filepath.lower()
        if lower.endswith(".csv"):
            self._handle_csv(filepath)
        elif lower.endswith((".shp", ".dbf", ".shx")):
            self._handle_shapefile_component(filepath)

    def _handle_csv(self, filepath: str):
        """Queue CSV file for async processing."""
        if filepath in self._processing:
            return

        self._processing.add(filepath)
        filename = Path(filepath).name
        file_type = _classify_csv(filename)

        if file_type is None:
            logger.debug(f"Ignoring unrecognized CSV: {filename}")
            self._processing.discard(filepath)
            return

        logger.info(f"Detected {file_type} CSV change: {filename}")

        # Wait for file to finish being written (blocking in watchdog thread)
        if not _wait_for_stability(filepath):
            logger.warning(f"File did not stabilize: {filename}")
            self._processing.discard(filepath)
            return

        # Schedule async ingestion on the event loop
        future = asyncio.run_coroutine_threadsafe(
            self._process_csv(filepath, file_type), self._loop
        )
        future.add_done_callback(lambda _: self._processing.discard(filepath))

    async def _process_csv(self, filepath: str, file_type: str):
        """Process a CSV file asynchronously."""
        try:
            if file_type == "forecast":
                result = await ingest_forecast_csv(filepath)
            elif file_type == "alert":
                result = await ingest_alert_csv(filepath)
            else:
                return

            logger.info(f"CSV ingestion result: {result}")
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}", exc_info=True)

    def _handle_shapefile_component(self, filepath: str):
        """Queue Shapefile for conversion when components (.shp, .dbf, .shx) arrive."""
        shp_path = str(Path(filepath).with_suffix(".shp"))
        filename = Path(shp_path).name

        if not is_contour_shapefile(filename):
            return

        if shp_path in self._processing:
            return

        self._processing.add(shp_path)
        logger.info(f"Detected Shapefile component event for: {filename}")

        # Wait for all companions to stabilize and be written
        if not verify_shapefile_ready(shp_path, wait_seconds=3.0):
            logger.debug(f"Shapefile companions not fully ready yet: {filename}")
            self._processing.discard(shp_path)
            return

        # Run conversion asynchronously via executor to avoid blocking event loop
        future = asyncio.run_coroutine_threadsafe(
            self._process_shapefile(shp_path), self._loop
        )
        future.add_done_callback(lambda _: self._processing.discard(shp_path))

    async def _process_shapefile(self, shp_path: str):
        """Run shapefile to GeoJSON conversion."""
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, lambda: convert_shapefile_to_geojson(shp_path))
            if result:
                logger.info(f"Shapefile conversion successful: {result['filename']}")
        except Exception as e:
            logger.error(f"Error converting shapefile {shp_path}: {e}", exc_info=True)


class FileWatcherService:
    """
    Manages the filesystem observer and periodic fallback scan.
    """

    def __init__(self):
        self._observer: BaseObserver | None = None
        self._running = False

    def start(self, loop: asyncio.AbstractEventLoop):
        """Start the watchdog observer on the data directory."""
        watch_path = DATA_DIR
        os.makedirs(watch_path, exist_ok=True)

        handler = ExportDirectoryEventHandler(loop)
        self._observer = Observer()
        self._observer.schedule(handler, watch_path, recursive=False)
        self._observer.daemon = True
        self._observer.start()
        self._running = True

        logger.info(f"File watcher started on: {watch_path}")

    def stop(self):
        """Stop the watchdog observer."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._running = False
            logger.info("File watcher stopped.")

    @property
    def is_running(self) -> bool:
        return self._running


async def scan_directory():
    """
    Periodic fallback scan — processes all CSV files and Shapefiles
    in the data directory. Called by APScheduler every hour to catch any missed events.
    """
    watch_path = Path(DATA_DIR)
    if not watch_path.exists():
        logger.warning(f"Data directory does not exist: {watch_path}")
        return

    # 1. Process CSV files
    csv_files = list(watch_path.glob("*.csv"))
    if csv_files:
        logger.info(f"Periodic scan: found {len(csv_files)} CSV files")
        for csv_file in csv_files:
            file_type = _classify_csv(csv_file.name)
            if file_type == "forecast":
                await ingest_forecast_csv(str(csv_file))
            elif file_type == "alert":
                await ingest_alert_csv(str(csv_file))

    # 2. Process Shapefiles
    loop = asyncio.get_running_loop()
    converted = await loop.run_in_executor(None, convert_all_shapefiles)
    if converted:
        logger.info(f"Periodic scan: converted {len(converted)} new/updated shapefiles")
