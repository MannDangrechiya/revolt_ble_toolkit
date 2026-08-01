"""Tests for the cross-capture comparator (Module 6)."""

from __future__ import annotations

import struct
from datetime import UTC, datetime

from revolt_ble_toolkit.analyzers.compare import (
    CaptureComparator,
    CorrelationCategory,
    format_diff_report,
)
from revolt_ble_toolkit.analyzers.gatt import Characteristic, CharacteristicProperty, Service
from revolt_ble_toolkit.parsers.att import AttOpcode, AttPacket
from revolt_ble_toolkit.parsers.btsnoop.models import PacketDirection
from revolt_ble_toolkit.pipeline import PipelineResult

_NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _notify(handle: int, value: bytes, hci_number: int = 1) -> AttPacket:
    return AttPacket(
        hci_number=hci_number,
        timestamp=_NOW,
        direction=PacketDirection.CONTROLLER_TO_HOST,
        connection_handle=1,
        opcode=AttOpcode.HANDLE_VALUE_NOTIFICATION,
        parameters=struct.pack("<H", handle) + value,
    )


def _result(att_packets: list[AttPacket], services: list[Service] | None = None) -> PipelineResult:
    return PipelineResult(
        hci_packets=[], att_packets=att_packets, services=services or [], classified=[]
    )


def test_known_battery_uuid_high_confidence() -> None:
    service = Service(
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
    capture1 = _result([_notify(10, bytes([80]))], services=[service])
    capture2 = _result([_notify(10, bytes([50]))], services=[service])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.attribute_handle == 10
    assert diff.category is CorrelationCategory.BATTERY
    assert diff.confidence == 0.95
    assert diff.capture1_last_value == bytes([80])
    assert diff.capture2_last_value == bytes([50])
    assert diff.changed_byte_offsets == (0,)


def test_unchanged_handle_is_excluded() -> None:
    capture1 = _result([_notify(10, bytes([80]))])
    capture2 = _result([_notify(10, bytes([80]))])

    assert CaptureComparator().compare(capture1, capture2) == []


def test_charging_boolean_heuristic() -> None:
    capture1 = _result([_notify(20, b"\x00")])
    capture2 = _result([_notify(20, b"\x01")])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.category is CorrelationCategory.CHARGING


def test_ride_mode_enum_heuristic() -> None:
    capture1 = _result([_notify(30, b"\x01"), _notify(30, b"\x03")])
    capture2 = _result([_notify(30, b"\x02")])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.category is CorrelationCategory.RIDE_MODE


def test_battery_percentage_heuristic_without_uuid() -> None:
    capture1 = _result(
        [_notify(40, bytes([v])) for v in (80, 75, 70, 65, 60)]
    )  # 5+ distinct values, above ride-mode's small-enum cutoff
    capture2 = _result([_notify(40, bytes([50]))])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.category is CorrelationCategory.BATTERY
    assert diff.confidence == 0.5


def test_temperature_heuristic() -> None:
    capture1 = _result([_notify(50, struct.pack("<h", 22))])
    capture2 = _result([_notify(50, struct.pack("<h", 30))])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.category is CorrelationCategory.TEMPERATURE


def test_voltage_heuristic() -> None:
    capture1 = _result([_notify(60, struct.pack("<H", 3700))])
    capture2 = _result([_notify(60, struct.pack("<H", 3600))])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.category is CorrelationCategory.VOLTAGE


def test_voltage_centivolt_heuristic() -> None:
    capture1 = _result([_notify(65, struct.pack("<H", 370))])  # 3.70V in centivolts
    capture2 = _result([_notify(65, struct.pack("<H", 360))])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.category is CorrelationCategory.VOLTAGE
    assert diff.confidence == 0.3


def test_known_temperature_uuid_high_confidence() -> None:
    service = Service(
        connection_handle=1,
        start_handle=1,
        end_handle=20,
        uuid="1809",
        characteristics=(
            Characteristic(
                declaration_handle=9,
                value_handle=10,
                uuid="2a1c",
                properties=CharacteristicProperty.NOTIFY,
            ),
        ),
    )
    capture1 = _result([_notify(10, struct.pack("<h", 220))], services=[service])
    capture2 = _result([_notify(10, struct.pack("<h", 250))], services=[service])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.category is CorrelationCategory.TEMPERATURE
    assert diff.confidence == 0.95


def test_gps_heuristic() -> None:
    capture1 = _result([_notify(70, struct.pack("<f", 37.7749))])
    capture2 = _result([_notify(70, struct.pack("<f", 37.775))])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.category is CorrelationCategory.GPS


def test_correlate_with_no_values_is_unknown() -> None:
    # _correlate's empty-input guard: unreachable via the public compare()
    # API (a handle only ever appears with >=1 real value), but a cheap,
    # worthwhile safety net for a private helper other code could call.
    category, confidence, reason = CaptureComparator._correlate(None, [])

    assert category is CorrelationCategory.UNKNOWN
    assert confidence == 0.0
    assert reason == "no observed values"


def test_no_heuristic_match_is_unknown() -> None:
    capture1 = _result([_notify(80, b"\xde\xad\xbe\xef\x00")])
    capture2 = _result([_notify(80, b"\x00\xef\xbe\xad\xde")])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.category is CorrelationCategory.UNKNOWN
    assert diff.confidence == 0.0


def test_handle_only_present_in_one_capture() -> None:
    capture1 = _result([])
    capture2 = _result([_notify(90, b"\x01")])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.capture1_last_value is None
    assert diff.capture2_last_value == b"\x01"
    assert diff.changed_byte_offsets == ()  # can't offset-compare when one side is missing


def test_length_change_has_no_byte_offsets() -> None:
    capture1 = _result([_notify(100, b"\x01\x02")])
    capture2 = _result([_notify(100, b"\x01\x02\x03")])

    (diff,) = CaptureComparator().compare(capture1, capture2)

    assert diff.changed_byte_offsets == ()


def test_read_response_and_read_request_are_ignored() -> None:
    value1, value2 = b"\xaa\xbb\xcc", b"\xdd\xee\xff"  # 3 bytes: not relevant here anyway
    read_req = AttPacket(
        hci_number=1,
        timestamp=_NOW,
        direction=PacketDirection.HOST_TO_CONTROLLER,
        connection_handle=1,
        opcode=AttOpcode.READ_REQUEST,
        parameters=struct.pack("<H", 110),
    )
    read_resp1 = AttPacket(
        hci_number=2,
        timestamp=_NOW,
        direction=PacketDirection.CONTROLLER_TO_HOST,
        connection_handle=1,
        opcode=AttOpcode.READ_RESPONSE,
        parameters=value1,
    )
    read_resp2 = AttPacket(
        hci_number=2,
        timestamp=_NOW,
        direction=PacketDirection.CONTROLLER_TO_HOST,
        connection_handle=1,
        opcode=AttOpcode.READ_RESPONSE,
        parameters=value2,
    )
    capture1 = _result([read_req, read_resp1])
    capture2 = _result([read_req, read_resp2])

    assert CaptureComparator().compare(capture1, capture2) == []


def test_format_diff_report_empty() -> None:
    assert format_diff_report([]) == "No changed handles detected between the two captures.\n"


def test_format_diff_report_lists_each_diff() -> None:
    capture1 = _result([_notify(20, bytes([80]))])
    capture2 = _result([_notify(20, bytes([50]))])

    diffs = CaptureComparator().compare(capture1, capture2)
    report = format_diff_report(diffs)

    assert "handle 20" in report
    assert "before: 50" in report
    assert "after:  32" in report
