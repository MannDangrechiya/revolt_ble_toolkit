"""Pydantic schemas for Vehicle Commands."""

from __future__ import annotations

from pydantic import BaseModel


class VehicleCommandRequest(BaseModel):
    command_type: str  # PAIR, VS_ON, VS_OFF
    token: str | None = None


class VehicleCommandResponse(BaseModel):
    command_id: str
    vehicle_id: str
    status: str  # QUEUED, EXECUTED, FAILED
    message: str
