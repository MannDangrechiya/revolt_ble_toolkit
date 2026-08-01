"""Parser for Android BTSnoop HCI capture logs (``btsnoop_hci.log``).

Public API:

- :class:`BtSnoopHciParser` — reads a capture file and yields :class:`HciPacket`.
- :class:`HciPacket` / :class:`AclHeader` / :class:`BtSnoopFileHeader` — parsed data.
- :class:`HciPacketType` / :class:`PacketDirection` — classification enums.

See :mod:`revolt_ble_toolkit.parsers.btsnoop.parser` for format details.
"""

from __future__ import annotations

from revolt_ble_toolkit.parsers.btsnoop.models import (
    AclHeader,
    BtSnoopFileHeader,
    HciPacket,
    HciPacketType,
    PacketDirection,
)
from revolt_ble_toolkit.parsers.btsnoop.parser import BtSnoopHciParser

__all__ = [
    "AclHeader",
    "BtSnoopFileHeader",
    "BtSnoopHciParser",
    "HciPacket",
    "HciPacketType",
    "PacketDirection",
]
