"""
Pydantic response schemas for the REST API.
"""

from datetime import datetime
from pydantic import BaseModel, Field


# ─── Node Schemas ────────────────────────────────────────────────────────────

class NodeResponse(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    node_type: str
    alert_threshold: float
    warning_threshold: float
    danger_threshold: float
    current_water_level: float | None = None
    status: str = "normal"  # "normal", "alert", "warning", "danger"

    model_config = {"from_attributes": True}


# ─── Water Level / Forecast Schemas ──────────────────────────────────────────

class WaterLevelReadingResponse(BaseModel):
    timestamp: datetime
    seconds: float | None = None
    water_level: float

    model_config = {"from_attributes": True}


class ForecastResponse(BaseModel):
    node_id: str
    node_name: str
    latitude: float
    longitude: float
    alert_threshold: float
    warning_threshold: float
    danger_threshold: float
    readings: list[WaterLevelReadingResponse] = Field(default_factory=list)
    total_readings: int = 0


class LatestForecastResponse(BaseModel):
    node_id: str
    node_name: str
    latitude: float
    longitude: float
    distance_km: float | None = None
    latest_reading: WaterLevelReadingResponse | None = None
    alert_threshold: float
    warning_threshold: float
    danger_threshold: float
    status: str = "normal"


# ─── Alert Schemas ───────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    alert_definition_id: str
    onset_time: datetime | None = None
    end_time: datetime | None = None
    priority: str | None = None
    target_id: str | None = None
    target_type: str | None = None
    category: str | None = None
    peak_value: float | None = None
    peak_value_units: str | None = None
    peak_time: datetime | None = None
    is_active: bool = False

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse] = Field(default_factory=list)
    total_active: int = 0


# ─── Dashboard Schemas ──────────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_nodes: int = 0
    active_alerts: int = 0
    latest_update: datetime | None = None
    max_water_level: float | None = None
    max_water_level_node: str | None = None
    max_water_level_time: datetime | None = None  # when the peak occurs in the forecast
    nodes_in_alert: int = 0
    nodes_in_warning: int = 0
    nodes_in_danger: int = 0
