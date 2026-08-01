"""Notification manager for routing raw BLE notifications and decoding protocol payloads."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.live.models import (
    DecodedBatteryStatus,
    DecodedPairingResponse,
    DecodedTelemetryFrame,
    NotificationEvent,
)

logger = get_logger(__name__)


class NotificationManager:
    """Manages raw notification subscriptions and protocol payload decoding."""

    def __init__(self) -> None:
        self._raw_listeners: dict[str | None, list[Callable[[NotificationEvent], None]]] = {}
        self._decoded_listeners: list[Callable[[Any], None]] = []

    def subscribe(
        self,
        listener: Callable[[NotificationEvent], None],
        characteristic_uuid: str | None = None,
    ) -> None:
        """Subscribe to raw notification events for a specific characteristic or all (None)."""
        listeners = self._raw_listeners.setdefault(characteristic_uuid, [])
        if listener not in listeners:
            listeners.append(listener)

    def unsubscribe(
        self,
        listener: Callable[[NotificationEvent], None],
        characteristic_uuid: str | None = None,
    ) -> None:
        """Unsubscribe a raw notification listener."""
        if characteristic_uuid in self._raw_listeners:
            listeners = self._raw_listeners[characteristic_uuid]
            if listener in listeners:
                listeners.remove(listener)

    def subscribe_decoded(self, listener: Callable[[Any], None]) -> None:
        """Subscribe to decoded protocol payload objects."""
        if listener not in self._decoded_listeners:
            self._decoded_listeners.append(listener)

    def unsubscribe_decoded(self, listener: Callable[[Any], None]) -> None:
        """Unsubscribe a decoded payload listener."""
        if listener in self._decoded_listeners:
            self._decoded_listeners.remove(listener)

    def handle_notification(self, event: NotificationEvent) -> None:
        """Dispatch a raw notification event and decode known payloads."""
        # 1. Dispatch raw listeners
        all_listeners = self._raw_listeners.get(None, [])
        specific_listeners = self._raw_listeners.get(event.characteristic_uuid, [])

        for listener in list(all_listeners + specific_listeners):
            try:
                listener(event)
            except Exception as exc:
                logger.error("Error in raw notification listener: %s", exc)

        # 2. Decode known protocol payloads
        decoded = self.decode_payload(event)
        if decoded is not None:
            for listener in list(self._decoded_listeners):
                try:
                    listener(decoded)
                except Exception as exc:
                    logger.error("Error in decoded payload listener: %s", exc)

    @staticmethod
    def decode_payload(event: NotificationEvent) -> Any | None:
        """Attempt to decode a raw notification event into a typed model."""
        value = event.value
        if not value:
            return None

        # Pairing response: ACCEPTED
        if value == b"ACCEPTED":
            return DecodedPairingResponse(
                timestamp=event.timestamp,
                success=True,
                message="ACCEPTED",
            )

        # Telemetry frame: LD,...
        try:
            text = value.decode("utf-8", errors="ignore")
            if text.startswith("LD,"):
                fields = text.split(",")
                return DecodedTelemetryFrame(
                    timestamp=event.timestamp,
                    raw_payload=text,
                    fields=fields,
                )
        except Exception:
            pass

        # Standard Battery Level: 1-byte 0-100%
        if len(value) == 1 and event.characteristic_uuid.startswith("00002a19"):
            battery_pct = value[0]
            if 0 <= battery_pct <= 100:
                return DecodedBatteryStatus(
                    timestamp=event.timestamp,
                    percentage=battery_pct,
                )

        return None
