"""
Dashboard aggregation endpoint — summary statistics for the frontend header.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Node, WaterLevelReading, AlertDefinition
from app.schemas import DashboardSummary
from app.routers.alerts import _is_alert_active
from app.routers.forecasts import _active_forecast_files, get_current_reading
from datetime import datetime


router = APIRouter(prefix="/api/v1", tags=["Dashboard"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """
    Return summary statistics for the dashboard header.
    Aggregates: total nodes, active alerts, latest update, peak water level.
    """
    # Evaluated on every request (a module-level datetime.now() would be
    # frozen at the moment the server started).
    now = datetime.now()  # same local clock as the CSV timestamps

    # Count the total number of nodes in the database
    node_count_result = await db.execute(select(func.count(Node.id)))
    total_nodes = node_count_result.scalar() or 0

    # Track active alert targets so node alerts are not double-counted.
    alerts_result = await db.execute(select(AlertDefinition))
    all_alerts = alerts_result.scalars().all()
    active_alert_targets: set[str] = set()
    active_system_alerts = 0
    for alert in all_alerts:
        if not _is_alert_active(alert):
            continue
        if alert.target_id:
            active_alert_targets.add(alert.target_id)
        else:
            active_system_alerts += 1

    # Latest update timestamp (when data was last ingested)
    active_forecast_files = _active_forecast_files()
    latest_result = await db.execute(
        select(func.max(WaterLevelReading.timestamp))
        .where(WaterLevelReading.source_file.in_(active_forecast_files))
    )
    latest_update = latest_result.scalar_one_or_none()

    # Peak = highest reading from forecast files currently present in DATA_DIR.
    peak = (await db.execute(
        select(WaterLevelReading.node_id, WaterLevelReading.water_level, WaterLevelReading.timestamp)
        .where(WaterLevelReading.source_file.in_(active_forecast_files))
        .order_by(desc(WaterLevelReading.water_level))
        .limit(1)
    )).first()
    max_level = peak.water_level if peak else None
    max_level_node = peak.node_id if peak else None
    max_level_time = peak.timestamp if peak else None

    # Count nodes per status using each node's CURRENT level
    nodes_result = await db.execute(select(Node))
    nodes = nodes_result.scalars().all()

    nodes_alert = 0
    nodes_warning = 0
    nodes_danger = 0
    threshold_alert_nodes: set[str] = set()

    for node in nodes:
        current = await get_current_reading(db, node.id, now)
        level = current.water_level if current else None
        if level is None:
            continue

        if level >= node.danger_threshold:
            nodes_danger += 1
            threshold_alert_nodes.add(node.id)
        elif level >= node.warning_threshold:
            nodes_warning += 1
            threshold_alert_nodes.add(node.id)
        elif level >= node.alert_threshold:
            nodes_alert += 1
            threshold_alert_nodes.add(node.id)

    active_alerts = len(active_alert_targets | threshold_alert_nodes) + active_system_alerts

    return DashboardSummary(
        total_nodes=total_nodes,
        active_alerts=active_alerts,
        latest_update=latest_update,
        max_water_level=max_level,
        max_water_level_node=max_level_node,
        #max_water_level_time=max_level_time,
        nodes_in_alert=nodes_alert,
        nodes_in_warning=nodes_warning,
        nodes_in_danger=nodes_danger,
    )

''' OLD CODE
@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """
    Return summary statistics for the dashboard header.
    Aggregates: total nodes, active alerts, latest update, max water level.
    """

    # Total nodes
    node_count_result = await db.execute(select(func.count(Node.id)))
    total_nodes = node_count_result.scalar() or 0

    # Active alerts
    alerts_result = await db.execute(select(AlertDefinition))
    all_alerts = alerts_result.scalars().all()
    active_alerts = sum(1 for a in all_alerts if _is_alert_active(a))

    # Latest update timestamp
    latest_result = await db.execute(
        select(WaterLevelReading.ingested_at)
        .order_by(desc(WaterLevelReading.ingested_at))
        .limit(1)
    )
    latest_update = latest_result.scalar_one_or_none()

    # Max water level across all nodes (latest readings only)
    # Get the latest reading per node and find the max
    nodes_result = await db.execute(select(Node))
    nodes = nodes_result.scalars().all()

    # Initialize max level tracking
    max_level = None
    max_level_node = None
    nodes_alert = 0
    nodes_warning = 0
    nodes_danger = 0

    peak = (await db.execute(
        select(WaterLevelReading.node_id, WaterLevelReading.water_level, WaterLevelReading.timestamp)
        .order_by(desc(WaterLevelReading.water_level)).limit(1)
    )).first()
    max_level = peak.water_level if peak else None
    max_level_node = peak.node_id if peak else None
    max_level_time = peak.timestamp if peak else None

    for node in nodes:
        # Get the latest water level reading for this node
        latest_reading_result = await db.execute(
            select(WaterLevelReading.water_level)
            .where(WaterLevelReading.node_id == node.id)
            .order_by(desc(WaterLevelReading.timestamp))
            .limit(1)
        )
        level = latest_reading_result.scalar_one_or_none()

        # Update max level tracking
        if level is not None:
            if max_level is None or level > max_level:
                max_level = level
                max_level_node = node.id

            # Count nodes in alert/warning/danger based on thresholds
            if level >= node.danger_threshold:
                nodes_danger += 1
            elif level >= node.warning_threshold:
                nodes_warning += 1
            elif level >= node.alert_threshold:
                nodes_alert += 1

    # Return the aggregated summary
    return DashboardSummary(
        total_nodes=total_nodes,
        active_alerts=active_alerts,
        latest_update=latest_update,
        max_water_level=max_level,
        max_water_level_node=max_level_node,
        nodes_in_alert=nodes_alert,
        nodes_in_warning=nodes_warning,
        nodes_in_danger=nodes_danger,
    )
'''

