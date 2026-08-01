"""Shared enumerations for the toolkit's domain layer."""

from __future__ import annotations

from enum import Enum, auto


class CaptureFormat(Enum):
    """Known capture log formats the toolkit will support."""

    ANDROID_HCI_SNOOP = auto()
    BTSNOOP = auto()
    UNKNOWN = auto()


class TransportType(Enum):
    """Bluetooth transport a captured record belongs to."""

    CLASSIC = auto()
    LOW_ENERGY = auto()
    UNKNOWN = auto()
