"""Tests for the plugin manager and plugin interfaces."""

from __future__ import annotations

from typing import Any

from revolt_ble_toolkit.live import (
    BlePlugin,
    ConnectionState,
    ConnectionStateEvent,
    NotificationEvent,
    PluginManager,
    WriteEvent,
)


class MockPlugin(BlePlugin):
    name = "MockPlugin"

    def __init__(self) -> None:
        self.state_events: list[ConnectionStateEvent] = []
        self.notifications: list[NotificationEvent] = []
        self.writes: list[WriteEvent] = []
        self.decoded: list[Any] = []

    def on_state_change(self, event: ConnectionStateEvent) -> None:
        self.state_events.append(event)

    def on_notification(self, event: NotificationEvent) -> None:
        self.notifications.append(event)

    def on_write(self, event: WriteEvent) -> None:
        self.writes.append(event)

    def on_decoded_payload(self, payload: Any) -> None:
        self.decoded.append(payload)


def test_plugin_lifecycle_hooks() -> None:
    pm = PluginManager()
    plugin = MockPlugin()
    pm.register(plugin)

    assert pm.registered_plugins == [plugin]

    state_event = ConnectionStateEvent(
        previous_state=ConnectionState.DISCONNECTED,
        new_state=ConnectionState.CONNECTED,
        reason="Connected",
        timestamp=None,  # type: ignore[arg-type]
    )
    pm.notify_state_change(state_event)

    assert len(plugin.state_events) == 1
    assert plugin.state_events[0] == state_event

    pm.unregister(plugin)
    assert pm.registered_plugins == []
