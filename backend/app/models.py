"""
SQLAlchemy ORM models for the flood forecasting platform.
"""

from datetime import datetime

from sqlalchemy import String, Float, DateTime, Boolean, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Node(Base):
    """Monitoring node with GIS coordinates and alert thresholds."""

    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    node_type: Mapped[str] = mapped_column(String(64), default="drain")
    alert_threshold: Mapped[float] = mapped_column(Float, default=2.0)
    warning_threshold: Mapped[float] = mapped_column(Float, default=3.0)
    danger_threshold: Mapped[float] = mapped_column(Float, default=4.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WaterLevelReading(Base):
    """Time-series water level reading from ICM forecast simulation."""

    __tablename__ = "water_level_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    seconds: Mapped[float] = mapped_column(Float, nullable=True)
    water_level: Mapped[float] = mapped_column(Float, nullable=False)
    source_file: Mapped[str] = mapped_column(String(512), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        # Composite unique constraint for upsert logic — prevents duplicate readings
        {"sqlite_autoincrement": True},
    )


class AlertDefinition(Base):
    """Alert/warning definition from ICM Live data export."""

    __tablename__ = "alert_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_definition_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    onset_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    priority: Mapped[str] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=True)
    category: Mapped[str] = mapped_column(String(128), nullable=True)
    peak_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_value_units: Mapped[str] = mapped_column(String(32), nullable=True)
    peak_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_file: Mapped[str] = mapped_column(String(512), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FileIngestLog(Base):
    """Tracks processed files to prevent re-ingestion of unchanged data."""

    __tablename__ = "file_ingest_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filepath: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "forecast" or "alert"
    rows_processed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="success")  # "success", "error", "partial"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
