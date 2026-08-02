"""Pydantic schemas for Telemetry Records."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TelemetryRecordResponse(BaseModel):
    id: str
    vehicle_id: str
    timestamp: datetime
    event_type: str
    battery_percentage: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    speed_kmh: float | None = None
    raw_payload: str

    model_config = ConfigDict(from_attributes=True)
