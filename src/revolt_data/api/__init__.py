"""API package for revolt_data."""

from __future__ import annotations

from revolt_data.api.auth import router as auth_router
from revolt_data.api.commands import router as commands_router
from revolt_data.api.telemetry import router as telemetry_router
from revolt_data.api.trips import router as trips_router
from revolt_data.api.users import router as users_router
from revolt_data.api.vehicles import router as vehicles_router
from revolt_data.api.websocket import router as ws_router

__all__ = [
    "auth_router",
    "commands_router",
    "telemetry_router",
    "trips_router",
    "users_router",
    "vehicles_router",
    "ws_router",
]
