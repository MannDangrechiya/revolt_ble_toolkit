"""Event, state, and decoded payload data models for the live BLE SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto


class ConnectionState(Enum):
    """Connection state enum for the BLE client state machine."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    AUTHENTICATING = auto()
    AUTHENTICATED = auto()
    RECONNECTING = auto()
    DISCONNECTING = auto()
    FAILED = auto()


@dataclass(frozen=True, slots=True)
class ConnectionStateEvent:
    """Emitted on every connection state machine state transition."""

    previous_state: ConnectionState
    new_state: ConnectionState
    reason: str
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class NotificationEvent:
    """A single notification/indication received from the device, verbatim."""

    timestamp: datetime
    characteristic_uuid: str
    value: bytes


@dataclass(frozen=True, slots=True)
class WriteEvent:
    """A single write sent to the device."""

    timestamp: datetime
    characteristic_uuid: str
    value: bytes


@dataclass(frozen=True, slots=True)
class CommandRequest:
    """A write command queued for transmission."""

    command_id: str
    characteristic_uuid: str
    payload: bytes
    timeout: float = 5.0
    retries: int = 3
    requires_response: bool = True
    priority: int = 10  # Lower number = higher priority


@dataclass(frozen=True, slots=True)
class DecodedTelemetryFrame:
    """Decoded comma-separated `LD,...` telemetry payload."""

    timestamp: datetime
    raw_payload: str
    fields: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DecodedPairingResponse:
    """Decoded pairing response payload (`ACCEPTED`)."""

    timestamp: datetime
    success: bool
    message: str


@dataclass(frozen=True, slots=True)
class DecodedBatteryStatus:
    """Decoded standard battery level payload (`0x2a19`)."""

    timestamp: datetime
    percentage: int
