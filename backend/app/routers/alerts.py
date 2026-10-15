"""
Alert API endpoints — active alerts and alert history.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AlertDefinition
from app.schemas import AlertResponse, AlertListResponse

router = APIRouter(prefix="/api/v1", tags=["Alerts"])


def _is_alert_active(alert: AlertDefinition) -> bool:
    # Determine if an alert is currently active based on onset/end times.
    now = datetime.now()

    # If no onset time, consider it active
    if alert.onset_time is None:
        return True

    # If onset is in the future, not active yet
    if alert.onset_time > now:
        return False

    # If no end time, consider active once onset has passed
    if alert.end_time is None:
        return alert.onset_time <= now

    return alert.onset_time <= now <= alert.end_time


@router.get("/alerts/active", response_model=AlertListResponse)
async def get_active_alerts(
    target_id: str | None = Query(None, description="Filter by target node ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return currently active/forecasted alert and warning thresholds.

    Plugin-friendly endpoint:
        GET /api/v1/alerts/active
    """
    result = await db.execute(
        select(AlertDefinition).order_by(desc(AlertDefinition.onset_time))
    )
    all_alerts = result.scalars().all()

    active_alerts = []
    for alert in all_alerts:
        is_active = _is_alert_active(alert)
        if not is_active:
            continue

        if target_id and alert.target_id != target_id:
            continue

        active_alerts.append(AlertResponse(
            alert_definition_id=alert.alert_definition_id,
            onset_time=alert.onset_time,
            end_time=alert.end_time,
            priority=alert.priority,
            target_id=alert.target_id,
            target_type=alert.target_type,
            category=alert.category,
            peak_value=alert.peak_value,
            peak_value_units=alert.peak_value_units,
            peak_time=alert.peak_time,
            is_active=True,
        ))

    # Sort by priority: Danger/Critical first, then Warning, then Alert, then others
        priority_order = {"danger": 0, "critical": 0, "warning": 1, "alert": 2, "info": 3}
        active_alerts.sort(
            key=lambda a: priority_order.get((a.priority or "").lower(), 99)
        )
    
    '''
    # Sort by priority: Critical first, then Warning, then others
    priority_order = {"critical": 0, "warning": 1, "info": 2}
    active_alerts.sort(
        key=lambda a: priority_order.get((a.priority or "").lower(), 99)
    )
    '''

    return AlertListResponse(
        alerts=active_alerts,
        total_active=len(active_alerts),
    )


@router.get("/alerts/history", response_model=AlertListResponse)
async def get_alert_history(
    target_id: str | None = Query(None, description="Filter by target node ID"),
    priority: str | None = Query(None, description="Filter by priority level"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return all alerts with optional filtering.

    Plugin-friendly endpoint:
        GET /api/v1/alerts/history?target_id=Drain_53&priority=Critical
    """
    query = select(AlertDefinition).order_by(desc(AlertDefinition.onset_time))

    if target_id:
        query = query.where(AlertDefinition.target_id == target_id)
    if priority:
        query = query.where(AlertDefinition.priority == priority)

    query = query.limit(limit)

    result = await db.execute(query)
    alerts = result.scalars().all()

    response_alerts = [
        AlertResponse(
            alert_definition_id=a.alert_definition_id,
            onset_time=a.onset_time,
            end_time=a.end_time,
            priority=a.priority,
            target_id=a.target_id,
            target_type=a.target_type,
            category=a.category,
            peak_value=a.peak_value,
            peak_value_units=a.peak_value_units,
            peak_time=a.peak_time,
            is_active=_is_alert_active(a),
        )
        for a in alerts
    ]

    active_count = sum(1 for a in response_alerts if a.is_active)

    return AlertListResponse(
        alerts=response_alerts,
        total_active=active_count,
    )
