"""Tests for the ATT parser (Module 2)."""

from __future__ import annotations

import struct
from datetime import UTC, datetime

from revolt_ble_toolkit.parsers.att import AttOpcode, AttParser
from revolt_ble_toolkit.parsers.btsnoop.models import (
    AclHeader,
    HciPacket,
    HciPacketType,
    PacketDirection,
)

_NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _acl_packet(
    l2cap: bytes,
    *,
    handle: int = 0x0040,
    direction: PacketDirection = PacketDirection.HOST_TO_CONTROLLER,
    packet_type: HciPacketType = HciPacketType.ACL_DATA,
    acl: AclHeader | None = None,
) -> HciPacket:
    if packet_type is HciPacketType.ACL_DATA and acl is None:
        acl = AclHeader(
            connection_handle=handle,
            packet_boundary_flag=0b10,
            broadcast_flag=0,
            data_total_length=len(l2cap),
            payload=l2cap,
        )
    return HciPacket(
        number=1,
        timestamp=_NOW,
        direction=direction,
        packet_type=packet_type,
        original_length=len(l2cap) + 5,
        included_length=len(l2cap) + 5,
        cumulative_drops=0,
        data=b"\x02" + l2cap,
        acl=acl,
    )


def _att_packet(opcode: int, params: bytes = b"", **kwargs: object) -> HciPacket:
    att_pdu = bytes([opcode]) + params
    l2cap = struct.pack("<HH", len(att_pdu), 0x0004) + att_pdu
    return _acl_packet(l2cap, **kwargs)  # type: ignore[arg-type]


def test_exchange_mtu_request() -> None:
    (att,) = list(AttParser().parse([_att_packet(0x02, struct.pack("<H", 247))]))
    assert att.opcode is AttOpcode.EXCHANGE_MTU_REQUEST
    assert att.exchanged_mtu == 247


def test_exchange_mtu_response() -> None:
    (att,) = list(AttParser().parse([_att_packet(0x03, struct.pack("<H", 185))]))
    assert att.opcode is AttOpcode.EXCHANGE_MTU_RESPONSE
    assert att.exchanged_mtu == 185


def test_read_request() -> None:
    (att,) = list(AttParser().parse([_att_packet(0x0A, struct.pack("<H", 0x0003))]))
    assert att.opcode is AttOpcode.READ_REQUEST
    assert att.attribute_handle == 0x0003
    assert att.value == b""


def test_read_response() -> None:
    (att,) = list(AttParser().parse([_att_packet(0x0B, b"\x01\x02\x03")]))
    assert att.opcode is AttOpcode.READ_RESPONSE
    assert att.attribute_handle is None
    assert att.value == b"\x01\x02\x03"


def test_write_request() -> None:
    params = struct.pack("<H", 0x0010) + b"\xaa\xbb"
    (att,) = list(AttParser().parse([_att_packet(0x12, params)]))
    assert att.opcode is AttOpcode.WRITE_REQUEST
    assert att.attribute_handle == 0x0010
    assert att.value == b"\xaa\xbb"


def test_write_command() -> None:
    params = struct.pack("<H", 0x0011) + b"\x01"
    (att,) = list(AttParser().parse([_att_packet(0x52, params)]))
    assert att.opcode is AttOpcode.WRITE_COMMAND
    assert att.attribute_handle == 0x0011
    assert att.value == b"\x01"


def test_notification() -> None:
    params = struct.pack("<H", 0x0025) + b"\x64"
    packet = _att_packet(0x1B, params, direction=PacketDirection.CONTROLLER_TO_HOST)
    (att,) = list(AttParser().parse([packet]))
    assert att.opcode is AttOpcode.HANDLE_VALUE_NOTIFICATION
    assert att.attribute_handle == 0x0025
    assert att.value == b"\x64"
    assert att.direction is PacketDirection.CONTROLLER_TO_HOST


def test_indication() -> None:
    params = struct.pack("<H", 0x0025) + b"\x65"
    packet = _att_packet(0x1D, params, direction=PacketDirection.CONTROLLER_TO_HOST)
    (att,) = list(AttParser().parse([packet]))
    assert att.opcode is AttOpcode.HANDLE_VALUE_INDICATION
    assert att.value == b"\x65"


def test_carries_hci_context() -> None:
    (att,) = list(AttParser().parse([_att_packet(0x0A, struct.pack("<H", 1), handle=0x0007)]))
    assert att.hci_number == 1
    assert att.timestamp == _NOW
    assert att.connection_handle == 0x0007


def test_skips_non_att_l2cap_channel() -> None:
    l2cap = struct.pack("<HH", 1, 0x0040) + b"\x00"  # SMP channel, not ATT
    assert list(AttParser().parse([_acl_packet(l2cap)])) == []


def test_skips_non_acl_packets() -> None:
    packet = _acl_packet(b"", packet_type=HciPacketType.COMMAND, acl=None)
    assert list(AttParser().parse([packet])) == []


def test_skips_unknown_att_opcode() -> None:
    assert list(AttParser().parse([_att_packet(0xFF)])) == []


def test_skips_l2cap_frame_too_short_for_header() -> None:
    assert list(AttParser().parse([_acl_packet(b"\x01\x02")])) == []
