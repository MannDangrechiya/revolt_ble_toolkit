"""Pydantic schemas for Vehicle Management."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VehicleCreate(BaseModel):
    vin: str
    name: str = "RV400"
    mac_address: str
    pairing_token: str


class VehicleStatusResponse(BaseModel):
    connection_state: str
    is_authenticated: bool
    ignition_on: bool
    battery_percentage: int
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)


class VehicleResponse(BaseModel):
    id: str
    owner_id: str
    vin: str
    name: str
    mac_address: str
    created_at: datetime
    status: VehicleStatusResponse | None = None

    model_config = ConfigDict(from_attributes=True)
