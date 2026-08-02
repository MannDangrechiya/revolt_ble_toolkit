"""Pydantic API schemas package for revolt_data."""

from __future__ import annotations

from revolt_data.schemas.auth import TokenResponse, UserLogin, UserRegister
from revolt_data.schemas.command import VehicleCommandRequest, VehicleCommandResponse
from revolt_data.schemas.telemetry import TelemetryRecordResponse
from revolt_data.schemas.trip import TripResponse
from revolt_data.schemas.user import UserResponse
from revolt_data.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleStatusResponse

__all__ = [
    "TelemetryRecordResponse",
    "TokenResponse",
    "TripResponse",
    "UserLogin",
    "UserRegister",
    "UserResponse",
    "VehicleCommandRequest",
    "VehicleCommandResponse",
    "VehicleCreate",
    "VehicleResponse",
    "VehicleStatusResponse",
]
