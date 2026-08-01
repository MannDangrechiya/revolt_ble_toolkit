"""Event objects for the live BLE client."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
