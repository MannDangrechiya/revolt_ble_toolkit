"""Helpers for building synthetic BTSnoop byte streams in tests.

Not a test module itself (no ``test_`` prefix) — imported by the actual
test modules to construct minimal, deterministic capture files byte by
byte instead of depending on a real ``btsnoop_hci.log`` sample.
"""

from __future__ import annotations

import struct
from datetime import datetime

from revolt_ble_toolkit.parsers.btsnoop import constants as c

DEFAULT_DATALINK_TYPE = 1002


def build_file_header(
    *, version: int = c.SUPPORTED_VERSION, datalink_type: int = DEFAULT_DATALINK_TYPE
) -> bytes:
    """Build a 16-byte BTSnoop file header."""
    return c.IDENTIFICATION_PATTERN + struct.pack(">II", version, datalink_type)


def to_btsnoop_usec(when: datetime) -> int:
    """Convert an aware ``datetime`` to a BTSnoop-epoch microsecond timestamp."""
    unix_usec = round(when.timestamp() * 1_000_000)
    return unix_usec + c.BTSNOOP_EPOCH_OFFSET_USEC


def build_record(
    *,
    data: bytes,
    received: bool,
    timestamp: datetime,
    original_length: int | None = None,
    cumulative_drops: int = 0,
) -> bytes:
    """Build one 24-byte record header plus ``data``."""
    included_length = len(data)
    original_length = included_length if original_length is None else original_length
    flags = 1 if received else 0
    ts_usec = to_btsnoop_usec(timestamp)
    header = struct.pack(
        c.RECORD_HEADER_STRUCT,
        original_length,
        included_length,
        flags,
        cumulative_drops,
        ts_usec,
    )
    return header + data


def command_packet_data(payload: bytes = b"\x00\x10\x00") -> bytes:
    """H4-framed HCI Command packet: indicator + opcode(2) + params, arbitrary here."""
    return bytes([c.H4_COMMAND]) + payload


def event_packet_data(payload: bytes = b"\x0e\x04\x01\x00\x10\x00") -> bytes:
    """H4-framed HCI Event packet: indicator + event code + params, arbitrary here."""
    return bytes([c.H4_EVENT]) + payload


def acl_packet_data(
    *,
    connection_handle: int,
    packet_boundary_flag: int = 0b10,
    broadcast_flag: int = 0b00,
    payload: bytes = b"\xaa\xbb\xcc",
) -> bytes:
    """H4-framed HCI ACL Data packet: indicator + ACL header + payload."""
    handle_and_flags = (
        (connection_handle & c.ACL_HANDLE_MASK)
        | ((packet_boundary_flag & c.ACL_PB_FLAG_MASK) << c.ACL_PB_FLAG_SHIFT)
        | ((broadcast_flag & c.ACL_BC_FLAG_MASK) << c.ACL_BC_FLAG_SHIFT)
    )
    acl_header = struct.pack("<HH", handle_and_flags, len(payload))
    return bytes([c.H4_ACL_DATA]) + acl_header + payload
