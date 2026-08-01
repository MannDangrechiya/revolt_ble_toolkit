"""Capture-log parsers.

``BaseLogParser`` is the generic extension point for future pipeline
integration; ``BtSnoopHciParser`` is the concrete, standalone parser for
Android BTSnoop HCI capture logs (``btsnoop_hci.log``).
"""

from __future__ import annotations

from revolt_ble_toolkit.parsers.att import AttOpcode, AttPacket, AttParser
from revolt_ble_toolkit.parsers.base import BaseLogParser
from revolt_ble_toolkit.parsers.btsnoop import (
    AclHeader,
    BtSnoopFileHeader,
    BtSnoopHciParser,
    HciPacket,
    HciPacketType,
    PacketDirection,
)

__all__ = [
    "AclHeader",
    "AttOpcode",
    "AttPacket",
    "AttParser",
    "BaseLogParser",
    "BtSnoopFileHeader",
    "BtSnoopHciParser",
    "HciPacket",
    "HciPacketType",
    "PacketDirection",
]
