"""Tests for the protocol analyzer (Module 4)."""

from __future__ import annotations

import struct
from datetime import UTC, datetime, timedelta

from revolt_ble_toolkit.analyzers.gatt import (
    Characteristic,
    CharacteristicProperty,
    Descriptor,
    Service,
)
from revolt_ble_toolkit.analyzers.protocol import (
    ClassifiedPacket,
    PacketCategory,
    ProtocolAnalyzer,
    generate_report,
)
from revolt_ble_toolkit.parsers.att import AttOpcode, AttPacket
from revolt_ble_toolkit.parsers.btsnoop.models import PacketDirection

_BASE = datetime(2024, 1, 1, tzinfo=UTC)


def _att(
    opcode: AttOpcode,
    params: bytes = b"",
    *,
    conn: int = 1,
    hci_number: int = 1,
    when: datetime = _BASE,
) -> AttPacket:
    return AttPacket(
        hci_number=hci_number,
        timestamp=when,
        direction=PacketDirection.CONTROLLER_TO_HOST,
        connection_handle=conn,
        opcode=opcode,
        parameters=params,
    )


def _handle_pdu(opcode: AttOpcode, handle: int, value: bytes = b"") -> bytes:
    return struct.pack("<H", handle) + value


def test_known_telemetry_uuid_wins_over_behavior() -> None:
    battery_service = Service(
        connection_handle=1,
        start_handle=1,
        end_handle=20,
        uuid="180f",
        characteristics=(
            Characteristic(
                declaration_handle=9,
                value_handle=10,
                uuid="2a19",
                properties=CharacteristicProperty.NOTIFY,
            ),
        ),
    )
    packet = _att(
        AttOpcode.HANDLE_VALUE_NOTIFICATION,
        _handle_pdu(AttOpcode.HANDLE_VALUE_NOTIFICATION, 10, b"\x64"),
    )

    (result,) = ProtocolAnalyzer().classify([packet], [battery_service])

    assert result.category is PacketCategory.TELEMETRY
    assert result.confidence == 0.9


def test_known_firmware_uuid_via_read_response_correlation() -> None:
    dfu_service = Service(
        connection_handle=1,
        start_handle=1,
        end_handle=20,
        uuid="180a",
        characteristics=(
            Characteristic(
                declaration_handle=19,
                value_handle=20,
                uuid="2a26",
                properties=CharacteristicProperty.READ,
            ),
        ),
    )
    read_request = _att(AttOpcode.READ_REQUEST, _handle_pdu(AttOpcode.READ_REQUEST, 20))
    read_response = _att(AttOpcode.READ_RESPONSE, b"1.2.3")

    results = ProtocolAnalyzer().classify([read_request, read_response], [dfu_service])

    assert results[1].category is PacketCategory.FIRMWARE


def test_cccd_write_is_configuration_via_known_uuid() -> None:
    service = Service(
        connection_handle=1,
        start_handle=1,
        end_handle=20,
        uuid="1801",
        characteristics=(
            Characteristic(
                declaration_handle=10,
                value_handle=11,
                uuid="2a05",
                properties=CharacteristicProperty.NOTIFY,
                descriptors=(Descriptor(handle=12, uuid="2902"),),
            ),
        ),
    )
    packet = _att(AttOpcode.WRITE_REQUEST, _handle_pdu(AttOpcode.WRITE_REQUEST, 12, b"\x01\x00"))

    (result,) = ProtocolAnalyzer().classify([packet], [service])

    assert result.category is PacketCategory.CONFIGURATION
    assert result.confidence == 0.85


def test_exchange_mtu_is_configuration() -> None:
    packet = _att(AttOpcode.EXCHANGE_MTU_REQUEST, struct.pack("<H", 247))

    (result,) = ProtocolAnalyzer().classify([packet])

    assert result.category is PacketCategory.CONFIGURATION
    assert result.confidence == 0.8


def test_gatt_discovery_response_is_configuration() -> None:
    packet = _att(AttOpcode.READ_BY_GROUP_TYPE_RESPONSE, b"\x06\x01\x00\x05\x00\x00\x18")

    (result,) = ProtocolAnalyzer().classify([packet])

    assert result.category is PacketCategory.CONFIGURATION
    assert result.confidence == 0.6


def test_heartbeat_from_regular_small_identical_notifications() -> None:
    packets = [
        _att(
            AttOpcode.HANDLE_VALUE_NOTIFICATION,
            _handle_pdu(AttOpcode.HANDLE_VALUE_NOTIFICATION, 50, b"\x01"),
            when=_BASE + timedelta(seconds=i),
            hci_number=i,
        )
        for i in range(5)
    ]

    results = ProtocolAnalyzer().classify(packets)

    assert all(r.category is PacketCategory.HEARTBEAT for r in results)
    assert results[0].confidence == 0.65


def test_telemetry_from_changing_values_without_known_uuid() -> None:
    deltas = [0.1, 5.0, 0.2, 3.0]
    when = _BASE
    packets = []
    for i, value in enumerate([b"\x01\x02", b"\x03\x04", b"\x05\x06", b"\x07\x08"]):
        packets.append(
            _att(
                AttOpcode.HANDLE_VALUE_NOTIFICATION,
                _handle_pdu(AttOpcode.HANDLE_VALUE_NOTIFICATION, 60, value),
                when=when,
                hci_number=i,
            )
        )
        when = when + timedelta(seconds=deltas[i])

    results = ProtocolAnalyzer().classify(packets)

    assert all(r.category is PacketCategory.TELEMETRY for r in results)
    assert results[0].confidence == 0.5


def test_firmware_from_burst_of_large_write_commands() -> None:
    packets = [
        _att(
            AttOpcode.WRITE_COMMAND,
            _handle_pdu(AttOpcode.WRITE_COMMAND, 70, bytes(20)),
            hci_number=i,
        )
        for i in range(5)
    ]

    results = ProtocolAnalyzer().classify(packets)

    assert all(r.category is PacketCategory.FIRMWARE for r in results)
    assert results[0].confidence == 0.7


def test_authentication_from_key_sized_high_entropy_write_request() -> None:
    packet = _att(
        AttOpcode.WRITE_REQUEST, _handle_pdu(AttOpcode.WRITE_REQUEST, 80, bytes(range(16)))
    )

    (result,) = ProtocolAnalyzer().classify([packet])

    assert result.category is PacketCategory.AUTHENTICATION
    assert result.confidence == 0.6


def test_generic_write_falls_back_to_configuration() -> None:
    packet = _att(AttOpcode.WRITE_REQUEST, _handle_pdu(AttOpcode.WRITE_REQUEST, 90, b"\x01"))

    (result,) = ProtocolAnalyzer().classify([packet])

    assert result.category is PacketCategory.CONFIGURATION
    assert result.confidence == 0.4


def test_orphan_read_response_with_no_prior_request_is_unknown() -> None:
    packet = _att(AttOpcode.READ_RESPONSE, b"\x01\x02")

    (result,) = ProtocolAnalyzer().classify([packet])

    assert result.category is PacketCategory.UNKNOWN
    assert result.confidence == 0.0


def test_unmatched_lone_read_request_is_unknown() -> None:
    packet = _att(AttOpcode.READ_REQUEST, _handle_pdu(AttOpcode.READ_REQUEST, 100))

    (result,) = ProtocolAnalyzer().classify([packet])

    assert result.category is PacketCategory.UNKNOWN
    assert result.confidence == 0.0


def test_preserves_original_packet_order() -> None:
    packets = [
        _att(AttOpcode.EXCHANGE_MTU_REQUEST, struct.pack("<H", 247), hci_number=1),
        _att(
            AttOpcode.WRITE_REQUEST, _handle_pdu(AttOpcode.WRITE_REQUEST, 90, b"\x01"), hci_number=2
        ),
        _att(AttOpcode.READ_REQUEST, _handle_pdu(AttOpcode.READ_REQUEST, 100), hci_number=3),
    ]

    results = ProtocolAnalyzer().classify(packets)

    assert [r.packet.hci_number for r in results] == [1, 2, 3]


def test_generate_report_counts_and_average_confidence() -> None:
    classified = [
        ClassifiedPacket(_att(AttOpcode.READ_RESPONSE), PacketCategory.TELEMETRY, 0.9, "x"),
        ClassifiedPacket(_att(AttOpcode.READ_RESPONSE), PacketCategory.TELEMETRY, 0.5, "y"),
        ClassifiedPacket(_att(AttOpcode.WRITE_REQUEST), PacketCategory.CONFIGURATION, 0.4, "z"),
    ]

    report = generate_report(classified)

    assert "3 packets" in report
    assert "telemetry" in report
    assert "2 packets  avg confidence 0.70" in report
    assert "configuration" in report
    assert "1 packets  avg confidence 0.40" in report


def test_generate_report_empty() -> None:
    assert generate_report([]) == "No packets classified.\n"
