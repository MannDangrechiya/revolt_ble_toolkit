"""Object model for automatic ATT protocol-role classification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from revolt_ble_toolkit.parsers.att import AttPacket


class PacketCategory(Enum):
    """Likely protocol role of an ATT packet, per heuristic classification."""

    AUTHENTICATION = "authentication"
    TELEMETRY = "telemetry"
    CONFIGURATION = "configuration"
    HEARTBEAT = "heartbeat"
    FIRMWARE = "firmware"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ClassifiedPacket:
    """An ATT packet plus its heuristic classification."""

    packet: AttPacket
    category: PacketCategory
    confidence: float  # 0.0-1.0
    reason: str
