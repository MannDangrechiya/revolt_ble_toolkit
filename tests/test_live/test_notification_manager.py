"""Tests for notification manager and payload decoders."""

from __future__ import annotations

from datetime import UTC, datetime

from revolt_ble_toolkit.live import (
    DecodedBatteryStatus,
    DecodedPairingResponse,
    DecodedTelemetryFrame,
    NotificationEvent,
    NotificationManager,
)

_CHAR_UUID = "49535343-1e4d-4bd9-ba61-23c647249616"


def test_notification_manager_dispatches_raw_and_decoded() -> None:
    nm = NotificationManager()
    raw_events: list[NotificationEvent] = []
    decoded_models: list[object] = []

    nm.subscribe(raw_events.append)
    nm.subscribe_decoded(decoded_models.append)

    event = NotificationEvent(
        timestamp=datetime.now(UTC),
        characteristic_uuid=_CHAR_UUID,
        value=b"ACCEPTED",
    )

    nm.handle_notification(event)

    assert len(raw_events) == 1
    assert raw_events[0] == event

    assert len(decoded_models) == 1
    assert isinstance(decoded_models[0], DecodedPairingResponse)
    assert decoded_models[0].success is True


def test_decode_telemetry_frame() -> None:
    nm = NotificationManager()
    event = NotificationEvent(
        timestamp=datetime.now(UTC),
        characteristic_uuid=_CHAR_UUID,
        value=b"LD,DEV123,12.34,56.78,1600000000",
    )

    decoded = nm.decode_payload(event)

    assert isinstance(decoded, DecodedTelemetryFrame)
    assert decoded.fields == ["LD", "DEV123", "12.34", "56.78", "1600000000"]


def test_decode_battery_status() -> None:
    nm = NotificationManager()
    event = NotificationEvent(
        timestamp=datetime.now(UTC),
        characteristic_uuid="00002a19-0000-1000-8000-00805f9b34fb",
        value=b"\x50",  # 80%
    )

    decoded = nm.decode_payload(event)

    assert isinstance(decoded, DecodedBatteryStatus)
    assert decoded.percentage == 80
