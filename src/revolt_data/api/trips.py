"""FastAPI Trips & Ride History Router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from revolt_data.api.users import get_current_user
from revolt_data.database import get_db
from revolt_data.models.trip import Trip
from revolt_data.models.user import User
from revolt_data.models.vehicle import Vehicle
from revolt_data.schemas.trip import TripResponse

router = APIRouter(prefix="/vehicles/{vehicle_id}/trips", tags=["Ride History"])


@router.get("", response_model=list[TripResponse])
async def list_trips(
    vehicle_id: str,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[Trip]:
    """Retrieve ride history trips for a vehicle."""
    # Verify vehicle ownership
    v_stmt = select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.owner_id == current_user.id)
    v_res = await db.execute(v_stmt)
    if not v_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    stmt = select(Trip).where(Trip.vehicle_id == vehicle_id).order_by(Trip.start_time.desc())
    res = await db.execute(stmt)
    return list(res.scalars().all())
