"""Trip calculations and ride history service."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from revolt_data.models.trip import Trip


def calculate_haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate Great Circle distance in km between two lat/lon points."""
    r = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 3)


class TripService:
    """Trip analytics and ride history service."""

    @staticmethod
    async def get_active_trip(session: AsyncSession, vehicle_id: str) -> Trip | None:
        """Get current active trip in progress for a vehicle."""
        stmt = (
            select(Trip)
            .where(Trip.vehicle_id == vehicle_id, Trip.status == "IN_PROGRESS")
            .order_by(Trip.start_time.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def start_trip(
        session: AsyncSession, vehicle_id: str, battery_pct: int
    ) -> Trip:
        """Start a new ride history trip."""
        active = await TripService.get_active_trip(session, vehicle_id)
        if active:
            return active

        trip = Trip(
            id=str(uuid4()),
            vehicle_id=vehicle_id,
            start_time=datetime.now(UTC),
            start_battery_pct=battery_pct,
            end_battery_pct=battery_pct,
            status="IN_PROGRESS",
        )
        session.add(trip)
        await session.flush()
        return trip

    @staticmethod
    async def update_trip_metrics(
        session: AsyncSession,
        trip: Trip,
        speed_kmh: float | None = None,
        battery_pct: int | None = None,
    ) -> None:
        """Update metrics for an active trip."""
        if battery_pct is not None:
            trip.end_battery_pct = battery_pct

        if speed_kmh is not None and speed_kmh > 0 and speed_kmh > trip.max_speed_kmh:
            trip.max_speed_kmh = round(speed_kmh, 1)

    @staticmethod
    async def complete_trip(session: AsyncSession, trip: Trip) -> None:
        """Mark active trip as completed."""
        trip.end_time = datetime.now(UTC)
        trip.status = "COMPLETED"
