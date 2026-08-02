"""Background worker persisting decoded revolt_ble_toolkit events to database."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.live.models import (
    ConnectionStateEvent,
    DecodedBatteryStatus,
    DecodedPairingResponse,
    DecodedTelemetryFrame,
)
from revolt_data.database import AsyncSessionLocal
from revolt_data.models.telemetry import TelemetryRecord
from revolt_data.models.vehicle_status import VehicleStatus
from revolt_data.services.ble_manager import LiveBleManager
from revolt_data.services.trip_service import TripService

logger = get_logger(__name__)


class TelemetryWorker:
    """Async background worker for persisting decoded SDK events and managing trips."""

    def __init__(self) -> None:
        self._running = False
        self._queue: asyncio.Queue[tuple[str, str, Any]] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start worker loop and subscribe to BLE Manager events."""
        if not self._running:
            self._running = True
            LiveBleManager.get_instance().add_event_listener(self._on_ble_event)
            self._task = asyncio.create_task(self._process_loop())
            logger.info("TelemetryWorker background task started")

    async def stop(self) -> None:
        """Stop background worker loop."""
        self._running = False
        LiveBleManager.get_instance().remove_event_listener(self._on_ble_event)
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    def _on_ble_event(self, vehicle_id: str, event_type: str, data: Any) -> None:
        self._queue.put_nowait((vehicle_id, event_type, data))

    async def _process_loop(self) -> None:
        while self._running:
            try:
                vehicle_id, event_type, data = await self._queue.get()
                await self._handle_event(vehicle_id, event_type, data)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error processing telemetry worker event: %s", exc)
            finally:
                self._queue.task_done()

    async def _handle_event(self, vehicle_id: str, event_type: str, data: Any) -> None:
        async with AsyncSessionLocal() as session:
            # Fetch vehicle status
            stmt = select(VehicleStatus).where(VehicleStatus.vehicle_id == vehicle_id)
            res = await session.execute(stmt)
            status = res.scalars().first()

            if not status:
                status = VehicleStatus(
                    id=str(uuid4()),
                    vehicle_id=vehicle_id,
                    connection_state="DISCONNECTED",
                )
                session.add(status)

            status.last_seen = datetime.now(UTC)

            if event_type == "STATE_CHANGE" and isinstance(data, ConnectionStateEvent):
                status.connection_state = data.new_state.name
                if data.new_state.name == "AUTHENTICATED":
                    status.is_authenticated = True
                elif data.new_state.name in ("DISCONNECTED", "FAILED"):
                    status.is_authenticated = False
                    status.ignition_on = False

            elif event_type == "DECODED_PAYLOAD":
                if isinstance(data, DecodedBatteryStatus):
                    status.battery_percentage = data.percentage
                    record = TelemetryRecord(
                        id=str(uuid4()),
                        vehicle_id=vehicle_id,
                        timestamp=data.timestamp,
                        event_type="BATTERY_STATUS",
                        battery_percentage=data.percentage,
                        raw_payload=f"Battery: {data.percentage}%",
                    )
                    session.add(record)

                elif isinstance(data, DecodedPairingResponse):
                    status.is_authenticated = data.success
                    record = TelemetryRecord(
                        id=str(uuid4()),
                        vehicle_id=vehicle_id,
                        timestamp=data.timestamp,
                        event_type="PAIRING_ACK",
                        raw_payload=data.message,
                    )
                    session.add(record)

                elif isinstance(data, DecodedTelemetryFrame):
                    record = TelemetryRecord(
                        id=str(uuid4()),
                        vehicle_id=vehicle_id,
                        timestamp=data.timestamp,
                        event_type="TELEMETRY_FRAME",
                        raw_payload=data.raw_payload,
                    )
                    session.add(record)

                    # Manage trip status
                    if status.ignition_on:
                        active_trip = await TripService.get_active_trip(session, vehicle_id)
                        if not active_trip:
                            active_trip = await TripService.start_trip(
                                session, vehicle_id, status.battery_percentage
                            )
                        await TripService.update_trip_metrics(
                            session, active_trip, battery_pct=status.battery_percentage
                        )

            await session.commit()
