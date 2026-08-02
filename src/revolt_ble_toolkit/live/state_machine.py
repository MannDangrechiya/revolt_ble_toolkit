"""Connection state machine for managing BLE client states and transition events."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.live.models import ConnectionState, ConnectionStateEvent

logger = get_logger(__name__)


class ConnectionStateMachine:
    """Thread-safe connection state machine with transition listeners."""

    def __init__(self, initial_state: ConnectionState = ConnectionState.DISCONNECTED) -> None:
        self._state = initial_state
        self._listeners: list[Callable[[ConnectionStateEvent], None]] = []

    @property
    def current_state(self) -> ConnectionState:
        return self._state

    def add_listener(self, listener: Callable[[ConnectionStateEvent], None]) -> None:
        """Register a callback for state transition events."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[ConnectionStateEvent], None]) -> None:
        """Unregister a state transition callback."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def transition_to(self, new_state: ConnectionState, reason: str = "") -> ConnectionStateEvent:
        """Transition state machine to ``new_state`` and notify listeners."""
        previous_state = self._state
        if previous_state == new_state:
            return ConnectionStateEvent(
                previous_state=previous_state,
                new_state=new_state,
                reason=reason or "State unchanged",
                timestamp=datetime.now(UTC),
            )

        self._state = new_state
        event = ConnectionStateEvent(
            previous_state=previous_state,
            new_state=new_state,
            reason=reason,
            timestamp=datetime.now(UTC),
        )

        logger.info(
            "Connection state transition: %s -> %s (%s)",
            previous_state.name,
            new_state.name,
            reason,
        )

        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception as exc:
                logger.error("Error in connection state listener: %s", exc)

        return event
