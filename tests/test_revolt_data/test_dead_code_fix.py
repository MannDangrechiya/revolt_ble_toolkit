"""Tests for Haversine distance calculation, trip completion, and schema cleanup."""

from __future__ import annotations

import asyncio
import os
import pytest

os.environ.setdefault(
    "REVOLT_JWT_SECRET", "test_secret_key_that_is_at_least_32_bytes_long"
)

from revolt_data.database import AsyncSessionLocal, init_db
from revolt_data.schemas.command import VehicleCommandRequest
from revolt_data.services.trip_service import (
    TripService,
    calculate_haversine_distance,
)


def test_haversine_distance_calculation() -> None:
    """Test Haversine distance between two known lat/lon coordinates."""
    # New York (40.7128, -74.0060) to London (51.5074, -0.1278) ~5570 km
    dist = calculate_haversine_distance(40.7128, -74.0060, 51.5074, -0.1278)
    assert 5500 < dist < 5650


def test_trip_start_and_completion() -> None:
    """Test starting, updating, and completing an active trip."""

    async def run_test() -> None:
        await init_db()
        async with AsyncSessionLocal() as session:
            v_id = "test_veh_123"
            trip = await TripService.start_trip(session, v_id, battery_pct=95)
            assert trip.status == "IN_PROGRESS"

            await TripService.update_trip_metrics(
                session, trip, speed_kmh=45.0, battery_pct=90
            )
            assert trip.max_speed_kmh == 45.0
            assert trip.end_battery_pct == 90

            completed = await TripService.complete_active_trip_for_vehicle(session, v_id)
            assert completed is not None
            assert completed.status == "COMPLETED"
            assert completed.end_time is not None

    asyncio.run(run_test())


def test_command_request_schema_without_custom_payload() -> None:
    """Test that VehicleCommandRequest parses valid fields without dead custom_payload."""
    req = VehicleCommandRequest(command_type="VS_ON", token="abc123")
    assert req.command_type == "VS_ON"
    assert req.token == "abc123"
