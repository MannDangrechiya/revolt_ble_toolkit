"""Tests for the GATT analyzer (Module 3)."""

from __future__ import annotations

import struct
from datetime import UTC, datetime

from revolt_ble_toolkit.analyzers.gatt import CharacteristicProperty, GattAnalyzer
from revolt_ble_toolkit.analyzers.gatt.analyzer import _parse_uuid
from revolt_ble_toolkit.parsers.att import AttOpcode, AttPacket
from revolt_ble_toolkit.parsers.btsnoop.models import PacketDirection

_NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _att(opcode: AttOpcode, params: bytes, *, conn: int = 1) -> AttPacket:
    return AttPacket(
        hci_number=1,
        timestamp=_NOW,
        direction=PacketDirection.CONTROLLER_TO_HOST,
        connection_handle=conn,
        opcode=opcode,
        parameters=params,
    )


def _services_response(*entries: tuple[int, int, int]) -> bytes:
    """entries: (start_handle, end_handle, uuid16)"""
    body = b"".join(struct.pack("<HHH", start, end, uuid) for start, end, uuid in entries)
    return bytes([6]) + body


def _characteristics_response(*entries: tuple[int, int, int, int]) -> bytes:
    """entries: (declaration_handle, properties, value_handle, uuid16)"""
    body = b"".join(
        struct.pack("<HBH", decl, props, value) + struct.pack("<H", uuid)
        for decl, props, value, uuid in entries
    )
    return bytes([7]) + body


def _descriptors_response(*entries: tuple[int, int]) -> bytes:
    """entries: (handle, uuid16)"""
    body = b"".join(struct.pack("<HH", handle, uuid) for handle, uuid in entries)
    return bytes([1]) + body


def test_discovers_services_characteristics_and_descriptors() -> None:
    packets = [
        _att(
            AttOpcode.READ_BY_GROUP_TYPE_RESPONSE,
            _services_response((1, 5, 0x1800), (10, 20, 0x1801)),
        ),
        _att(
            AttOpcode.READ_BY_TYPE_RESPONSE,
            _characteristics_response(
                (2, CharacteristicProperty.READ, 3, 0x2A00),
                (11, CharacteristicProperty.NOTIFY, 12, 0x2A19),
            ),
        ),
        _att(AttOpcode.FIND_INFORMATION_RESPONSE, _descriptors_response((13, 0x2902))),
    ]

    services = sorted(GattAnalyzer().analyze(packets), key=lambda s: s.start_handle)

    assert len(services) == 2
    generic_access, second = services
    assert generic_access.uuid == "1800"
    assert generic_access.start_handle == 1
    assert generic_access.end_handle == 5
    assert generic_access.connection_handle == 1
    (device_name,) = generic_access.characteristics
    assert device_name.uuid == "2a00"
    assert device_name.declaration_handle == 2
    assert device_name.value_handle == 3
    assert device_name.properties == CharacteristicProperty.READ
    assert device_name.descriptors == ()

    assert second.uuid == "1801"
    (notifiable,) = second.characteristics
    assert notifiable.properties == CharacteristicProperty.NOTIFY
    (cccd,) = notifiable.descriptors
    assert cccd.handle == 13
    assert cccd.uuid == "2902"


def test_combined_properties_bitmask() -> None:
    packets = [
        _att(AttOpcode.READ_BY_GROUP_TYPE_RESPONSE, _services_response((1, 10, 0x1800))),
        _att(
            AttOpcode.READ_BY_TYPE_RESPONSE,
            _characteristics_response(
                (2, CharacteristicProperty.READ | CharacteristicProperty.WRITE, 3, 0x2A00)
            ),
        ),
    ]

    (service,) = GattAnalyzer().analyze(packets)
    (char,) = service.characteristics
    assert char.properties == (CharacteristicProperty.READ | CharacteristicProperty.WRITE)
    assert char.properties & CharacteristicProperty.NOTIFY == 0


def test_separates_by_connection_handle() -> None:
    packets = [
        _att(AttOpcode.READ_BY_GROUP_TYPE_RESPONSE, _services_response((1, 5, 0x1800)), conn=1),
        _att(AttOpcode.READ_BY_GROUP_TYPE_RESPONSE, _services_response((1, 5, 0x1801)), conn=2),
        _att(
            AttOpcode.READ_BY_TYPE_RESPONSE,
            _characteristics_response((2, CharacteristicProperty.READ, 3, 0x2A00)),
            conn=1,
        ),
    ]

    services = GattAnalyzer().analyze(packets)

    by_conn = {s.connection_handle: s for s in services}
    assert len(by_conn[1].characteristics) == 1
    assert len(by_conn[2].characteristics) == 0  # characteristic belongs to conn 1, not 2


def test_characteristic_outside_any_service_range_is_dropped() -> None:
    packets = [
        _att(AttOpcode.READ_BY_GROUP_TYPE_RESPONSE, _services_response((1, 5, 0x1800))),
        _att(
            AttOpcode.READ_BY_TYPE_RESPONSE,
            _characteristics_response((99, CharacteristicProperty.READ, 100, 0x2A00)),
        ),
    ]

    (service,) = GattAnalyzer().analyze(packets)

    assert service.characteristics == ()


def test_ignores_non_discovery_att_packets() -> None:
    packets = [_att(AttOpcode.READ_RESPONSE, b"\x01\x02\x03")]

    assert GattAnalyzer().analyze(packets) == []


def test_empty_input_returns_empty_list() -> None:
    assert GattAnalyzer().analyze([]) == []


def test_parse_uuid_short_form() -> None:
    assert _parse_uuid(struct.pack("<H", 0x180F)) == "180f"


def test_parse_uuid_128_bit() -> None:
    # Nordic UART Service UUID: 6e400001-b5a3-f393-e0a9-e50e24dcca9e
    canonical = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
    wire_bytes = bytes.fromhex(canonical.replace("-", ""))[::-1]
    assert _parse_uuid(wire_bytes) == canonical
