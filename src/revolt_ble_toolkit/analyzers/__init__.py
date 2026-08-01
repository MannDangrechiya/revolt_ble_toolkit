"""Packet/record analyzers.

``BaseAnalyzer`` is the generic extension point for future pipeline
integration; ``GattAnalyzer`` reconstructs the GATT hierarchy from decoded
ATT PDUs; ``ProtocolAnalyzer`` heuristically classifies ATT traffic by role;
``CaptureComparator`` diffs two captures and correlates what changed.
"""

from __future__ import annotations

from revolt_ble_toolkit.analyzers.base import BaseAnalyzer
from revolt_ble_toolkit.analyzers.compare import (
    CaptureComparator,
    CorrelationCategory,
    HandleDiff,
    compare_captures,
)
from revolt_ble_toolkit.analyzers.gatt import (
    Characteristic,
    CharacteristicProperty,
    Descriptor,
    GattAnalyzer,
    Service,
)
from revolt_ble_toolkit.analyzers.protocol import (
    ClassifiedPacket,
    PacketCategory,
    ProtocolAnalyzer,
    generate_report,
)

__all__ = [
    "BaseAnalyzer",
    "CaptureComparator",
    "Characteristic",
    "CharacteristicProperty",
    "ClassifiedPacket",
    "CorrelationCategory",
    "Descriptor",
    "GattAnalyzer",
    "HandleDiff",
    "PacketCategory",
    "ProtocolAnalyzer",
    "Service",
    "compare_captures",
    "generate_report",
]
