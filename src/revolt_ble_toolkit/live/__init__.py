"""Production-grade Live BLE communication SDK (Bleak-backed) for Revolt vehicles.

Requires the optional ``live`` extra: ``pip install -e ".[live]"``.
"""

from __future__ import annotations

from revolt_ble_toolkit.live.client import RevoltLiveClient
from revolt_ble_toolkit.live.heartbeat import HeartbeatManager
from revolt_ble_toolkit.live.models import (
    CommandRequest,
    ConnectionState,
    ConnectionStateEvent,
    DecodedBatteryStatus,
    DecodedPairingResponse,
    DecodedTelemetryFrame,
    NotificationEvent,
    WriteEvent,
)
from revolt_ble_toolkit.live.notification_manager import NotificationManager
from revolt_ble_toolkit.live.plugins import BlePlugin, PluginManager
from revolt_ble_toolkit.live.retry import RetryStrategy
from revolt_ble_toolkit.live.state_machine import ConnectionStateMachine
from revolt_ble_toolkit.live.write_queue import AsyncWriteQueue

__all__ = [
    "AsyncWriteQueue",
    "BlePlugin",
    "CommandRequest",
    "ConnectionState",
    "ConnectionStateEvent",
    "ConnectionStateMachine",
    "DecodedBatteryStatus",
    "DecodedPairingResponse",
    "DecodedTelemetryFrame",
    "HeartbeatManager",
    "NotificationEvent",
    "NotificationManager",
    "PluginManager",
    "RetryStrategy",
    "RevoltLiveClient",
    "WriteEvent",
]
