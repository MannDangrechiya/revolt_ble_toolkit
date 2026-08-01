"""Domain model for parsed ATT (Attribute Protocol) packets."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

from revolt_ble_toolkit.parsers.btsnoop.models import PacketDirection

# Opcodes that carry a 2-byte little-endian attribute handle right after the
# opcode byte.
_HANDLE_OPCODES = frozenset(
    {
        0x0A,  # Read Request
        0x12,  # Write Request
        0x52,  # Write Command
        0x1B,  # Handle Value Notification
        0x1D,  # Handle Value Indication
    }
)
_MTU_OPCODES = frozenset({0x02, 0x03})  # Exchange MTU Request / Response


class AttOpcode(IntEnum):
    """The ATT opcodes this module detects (see docs/att_parser.md)."""

    EXCHANGE_MTU_REQUEST = 0x02
    EXCHANGE_MTU_RESPONSE = 0x03
    FIND_INFORMATION_RESPONSE = 0x05  # descriptor discovery
    READ_BY_TYPE_RESPONSE = 0x09  # characteristic discovery
    READ_REQUEST = 0x0A
    READ_RESPONSE = 0x0B
    READ_BY_GROUP_TYPE_RESPONSE = 0x11  # service discovery
    WRITE_REQUEST = 0x12
    WRITE_COMMAND = 0x52
    HANDLE_VALUE_NOTIFICATION = 0x1B
    HANDLE_VALUE_INDICATION = 0x1D


@dataclass(frozen=True, slots=True)
class AttPacket:
    """A single parsed ATT PDU, carried inside an HCI ACL packet's L2CAP frame."""

    hci_number: int
    timestamp: datetime
    direction: PacketDirection
    connection_handle: int
    opcode: AttOpcode
    parameters: bytes  # raw ATT parameters, after the opcode byte

    @property
    def attribute_handle(self) -> int | None:
        """2-byte handle, for opcodes that carry one (None otherwise)."""
        if self.opcode not in _HANDLE_OPCODES or len(self.parameters) < 2:
            return None
        (handle,) = struct.unpack("<H", self.parameters[:2])
        return int(handle)

    @property
    def value(self) -> bytes:
        """Attribute value bytes (after the handle, or all parameters for Read Response)."""
        if self.opcode in _HANDLE_OPCODES:
            return self.parameters[2:]
        return self.parameters

    @property
    def exchanged_mtu(self) -> int | None:
        """MTU value, for Exchange MTU Request/Response (None otherwise)."""
        if self.opcode not in _MTU_OPCODES or len(self.parameters) < 2:
            return None
        (mtu,) = struct.unpack("<H", self.parameters[:2])
        return int(mtu)
