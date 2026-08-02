"""FastAPI Telemetry Records Router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from revolt_data.api.users import get_current_user
from revolt_data.database import get_db
from revolt_data.models.telemetry import TelemetryRecord
from revolt_data.models.user import User
from revolt_data.models.vehicle import Vehicle
from revolt_data.schemas.telemetry import TelemetryRecordResponse

router = APIRouter(prefix="/vehicles/{vehicle_id}/telemetry", tags=["Telemetry"])


@router.get("", response_model=list[TelemetryRecordResponse])
async def get_telemetry_history(
    vehicle_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[TelemetryRecord]:
    """Retrieve decoded telemetry time-series records for a vehicle."""
    v_stmt = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.owner_id == current_user.id)
    v_res = await db.execute(v_stmt)
    if not v_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    stmt = (
        select(TelemetryRecord)
        .where(TelemetryRecord.vehicle_id == vehicle_id)
        .order_by(TelemetryRecord.timestamp.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())
