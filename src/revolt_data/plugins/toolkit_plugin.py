"""RevoltDataBlePlugin - Custom plugin extending revolt_ble_toolkit.live.BlePlugin.

Bridges decoded BLE SDK events directly into revolt_data's persistence layer
and WebSocket broadcast engine without duplicating BLE parsing logic.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.live import BlePlugin
from revolt_ble_toolkit.live.models import ConnectionStateEvent, NotificationEvent, WriteEvent

logger = get_logger(__name__)


class RevoltDataBlePlugin(BlePlugin):
    """Bridge plugin forwarding decoded SDK events to revolt_data services."""

    name = "RevoltDataBlePlugin"

    def __init__(
        self,
        vehicle_id: str,
        event_dispatcher: Callable[[str, str, Any], None] | None = None,
    ) -> None:
        self.vehicle_id = vehicle_id
        self._event_dispatcher = event_dispatcher

    def on_state_change(self, event: ConnectionStateEvent) -> None:
        """Forward state transitions to event dispatcher."""
        logger.info(
            "Vehicle %s BLE state change: %s -> %s",
            self.vehicle_id,
            event.previous_state.name,
            event.new_state.name,
        )
        if self._event_dispatcher:
            self._event_dispatcher(self.vehicle_id, "STATE_CHANGE", event)

    def on_notification(self, event: NotificationEvent) -> None:
        """Forward raw notification events."""
        if self._event_dispatcher:
            self._event_dispatcher(self.vehicle_id, "RAW_NOTIFICATION", event)

    def on_decoded_payload(self, payload: Any) -> None:
        """Forward decoded protocol payloads (DecodedTelemetryFrame, DecodedBatteryStatus, etc.)."""
        logger.info("Vehicle %s decoded payload: %s", self.vehicle_id, type(payload).__name__)
        if self._event_dispatcher:
            self._event_dispatcher(self.vehicle_id, "DECODED_PAYLOAD", payload)

    def on_write(self, event: WriteEvent) -> None:
        """Forward write events."""
        if self._event_dispatcher:
            self._event_dispatcher(self.vehicle_id, "WRITE_EVENT", event)
