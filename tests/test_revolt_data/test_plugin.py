"""Tests for RevoltDataBlePlugin integration with revolt_ble_toolkit."""

from __future__ import annotations

from typing import Any

from revolt_ble_toolkit.live.models import (
    ConnectionState,
    ConnectionStateEvent,
    DecodedBatteryStatus,
)
from revolt_data.plugins import RevoltDataBlePlugin


def test_revolt_data_ble_plugin_forwards_events() -> None:
    events: list[tuple[str, str, Any]] = []

    def dispatcher(v_id: str, e_type: str, data: Any) -> None:
        events.append((v_id, e_type, data))

    plugin = RevoltDataBlePlugin(vehicle_id="v123", event_dispatcher=dispatcher)

    state_event = ConnectionStateEvent(
        previous_state=ConnectionState.DISCONNECTED,
        new_state=ConnectionState.CONNECTED,
        reason="Connected",
        timestamp=None,  # type: ignore[arg-type]
    )
    plugin.on_state_change(state_event)

    battery_event = DecodedBatteryStatus(timestamp=None, percentage=85)  # type: ignore[arg-type]
    plugin.on_decoded_payload(battery_event)

    assert len(events) == 2
    assert events[0] == ("v123", "STATE_CHANGE", state_event)
    assert events[1] == ("v123", "DECODED_PAYLOAD", battery_event)
