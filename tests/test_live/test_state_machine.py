"""Tests for the connection state machine."""

from __future__ import annotations

from revolt_ble_toolkit.live import ConnectionState, ConnectionStateEvent, ConnectionStateMachine


def test_initial_state_defaults_to_disconnected() -> None:
    sm = ConnectionStateMachine()
    assert sm.current_state is ConnectionState.DISCONNECTED


def test_transition_notifies_listeners() -> None:
    sm = ConnectionStateMachine()
    events: list[ConnectionStateEvent] = []
    sm.add_listener(events.append)

    sm.transition_to(ConnectionState.CONNECTING, "Connecting test")
    sm.transition_to(ConnectionState.CONNECTED, "Connected test")

    assert len(events) == 2
    assert events[0].previous_state is ConnectionState.DISCONNECTED
    assert events[0].new_state is ConnectionState.CONNECTING
    assert events[0].reason == "Connecting test"

    assert events[1].previous_state is ConnectionState.CONNECTING
    assert events[1].new_state is ConnectionState.CONNECTED


def test_remove_listener_stops_notifications() -> None:
    sm = ConnectionStateMachine()
    events: list[ConnectionStateEvent] = []
    sm.add_listener(events.append)
    sm.remove_listener(events.append)

    sm.transition_to(ConnectionState.CONNECTING)

    assert len(events) == 0
