"""SQLAlchemy ORM models package for revolt_data."""

from __future__ import annotations

from revolt_data.models.telemetry import TelemetryRecord
from revolt_data.models.trip import Trip
from revolt_data.models.user import User
from revolt_data.models.vehicle import Vehicle
from revolt_data.models.vehicle_status import VehicleStatus

__all__ = ["TelemetryRecord", "Trip", "User", "Vehicle", "VehicleStatus"]
