"""Pydantic schemas for Trips & Ride History."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TripResponse(BaseModel):
    id: str
    vehicle_id: str
    start_time: datetime
    end_time: datetime | None = None
    distance_km: float
    avg_speed_kmh: float
    max_speed_kmh: float
    start_battery_pct: int
    end_battery_pct: int
    status: str

    model_config = ConfigDict(from_attributes=True)
