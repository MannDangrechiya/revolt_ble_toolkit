"""Tests for the BTSnoop HCI parser (Module 1)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from revolt_ble_toolkit.core.exceptions import ParsingError
from revolt_ble_toolkit.parsers.btsnoop import (
    BtSnoopHciParser,
    HciPacketType,
    PacketDirection,
)
from revolt_ble_toolkit.parsers.btsnoop import constants as c
from tests.test_parsers.fixtures import (
    DEFAULT_DATALINK_TYPE,
    acl_packet_data,
    build_file_header,
    build_record,
    command_packet_data,
    event_packet_data,
)


def _write(tmp_path: Path, name: str, data: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


class TestFileHeader:
    def test_read_header_returns_version_and_datalink_type(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "btsnoop_hci.log", build_file_header())

        header = BtSnoopHciParser().read_header(path)

        assert header.identification == c.IDENTIFICATION_PATTERN
        assert header.version == c.SUPPORTED_VERSION
        assert header.datalink_type == DEFAULT_DATALINK_TYPE

    def test_rejects_bad_identification_pattern(self, tmp_path: Path) -> None:
        bad_header = b"not-btsnp" + b"\x00" * 7
        path = _write(tmp_path, "bad.log", bad_header)

        with pytest.raises(ParsingError, match="identification"):
            BtSnoopHciParser().read_header(path)

    def test_rejects_unsupported_version(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "bad.log", build_file_header(version=2))

        with pytest.raises(ParsingError, match="version"):
            BtSnoopHciParser().read_header(path)

    def test_rejects_file_shorter_than_header(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "bad.log", b"btsnoop\x00\x00\x00")

        with pytest.raises(ParsingError, match="smaller than"):
            BtSnoopHciParser().read_header(path)


class TestPacketParsing:
    def test_parses_command_and_event_with_direction_and_sequence(self, tmp_path: Path) -> None:
        t0 = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        t1 = datetime(2024, 1, 15, 12, 0, 1, tzinfo=UTC)
        data = build_file_header()
        data += build_record(data=command_packet_data(), received=False, timestamp=t0)
        data += build_record(data=event_packet_data(), received=True, timestamp=t1)
        path = _write(tmp_path, "btsnoop_hci.log", data)

        packets = list(BtSnoopHciParser().parse_file(path))

        assert [p.number for p in packets] == [1, 2]
        assert packets[0].packet_type is HciPacketType.COMMAND
        assert packets[0].direction is PacketDirection.HOST_TO_CONTROLLER
        assert packets[0].acl is None
        assert packets[1].packet_type is HciPacketType.EVENT
        assert packets[1].direction is PacketDirection.CONTROLLER_TO_HOST

    def test_parses_timestamps(self, tmp_path: Path) -> None:
        when = datetime(2023, 6, 1, 8, 30, 45, 123456, tzinfo=UTC)
        data = build_file_header()
        data += build_record(data=command_packet_data(), received=False, timestamp=when)
        path = _write(tmp_path, "btsnoop_hci.log", data)

        (packet,) = list(BtSnoopHciParser().parse_file(path))

        assert packet.timestamp == when

    def test_parses_packet_size_and_truncation(self, tmp_path: Path) -> None:
        payload = command_packet_data()
        data = build_file_header()
        data += build_record(
            data=payload,
            received=False,
            timestamp=datetime.now(tz=UTC),
            original_length=len(payload) + 50,
        )
        path = _write(tmp_path, "btsnoop_hci.log", data)

        (packet,) = list(BtSnoopHciParser().parse_file(path))

        assert packet.included_length == len(payload)
        assert packet.original_length == len(payload) + 50
        assert packet.is_truncated is True

    def test_untruncated_packet_reports_not_truncated(self, tmp_path: Path) -> None:
        payload = command_packet_data()
        data = build_file_header()
        data += build_record(data=payload, received=False, timestamp=datetime.now(tz=UTC))
        path = _write(tmp_path, "btsnoop_hci.log", data)

        (packet,) = list(BtSnoopHciParser().parse_file(path))

        assert packet.is_truncated is False

    def test_unknown_packet_type_indicator(self, tmp_path: Path) -> None:
        data = build_file_header()
        data += build_record(
            data=bytes([0xFF, 0x01, 0x02]),
            received=True,
            timestamp=datetime.now(tz=UTC),
        )
        path = _write(tmp_path, "btsnoop_hci.log", data)

        (packet,) = list(BtSnoopHciParser().parse_file(path))

        assert packet.packet_type is HciPacketType.UNKNOWN
        assert packet.acl is None


class TestAclParsing:
    def test_parses_connection_handle_and_flags(self, tmp_path: Path) -> None:
        payload = b"\x01\x02\x03\x04"
        acl_data = acl_packet_data(
            connection_handle=0x0041,
            packet_boundary_flag=0b10,
            broadcast_flag=0b00,
            payload=payload,
        )
        data = build_file_header()
        data += build_record(data=acl_data, received=False, timestamp=datetime.now(tz=UTC))
        path = _write(tmp_path, "btsnoop_hci.log", data)

        (packet,) = list(BtSnoopHciParser().parse_file(path))

        assert packet.packet_type is HciPacketType.ACL_DATA
        assert packet.acl is not None
        assert packet.acl.connection_handle == 0x0041
        assert packet.acl.packet_boundary_flag == 0b10
        assert packet.acl.broadcast_flag == 0b00
        assert packet.acl.data_total_length == len(payload)
        assert packet.acl.payload == payload

    def test_distinguishes_multiple_connection_handles(self, tmp_path: Path) -> None:
        now = datetime.now(tz=UTC)
        data = build_file_header()
        data += build_record(
            data=acl_packet_data(connection_handle=0x0001, payload=b"\x11"),
            received=False,
            timestamp=now,
        )
        data += build_record(
            data=acl_packet_data(connection_handle=0x0002, payload=b"\x22"),
            received=True,
            timestamp=now,
        )
        path = _write(tmp_path, "btsnoop_hci.log", data)

        packets = list(BtSnoopHciParser().parse_file(path))

        handles = [p.acl.connection_handle for p in packets if p.acl is not None]
        assert handles == [0x0001, 0x0002]

    def test_acl_header_too_short_leaves_acl_none(self, tmp_path: Path) -> None:
        data = build_file_header()
        data += build_record(
            data=bytes([c.H4_ACL_DATA, 0x01, 0x02]),  # only 2 bytes after indicator
            received=False,
            timestamp=datetime.now(tz=UTC),
        )
        path = _write(tmp_path, "btsnoop_hci.log", data)

        (packet,) = list(BtSnoopHciParser().parse_file(path))

        assert packet.packet_type is HciPacketType.ACL_DATA
        assert packet.acl is None


class TestErrorHandling:
    def test_truncated_record_header_raises(self, tmp_path: Path) -> None:
        data = build_file_header() + b"\x00" * 10  # less than a full 24-byte record header
        path = _write(tmp_path, "btsnoop_hci.log", data)

        with pytest.raises(ParsingError, match="truncated record header"):
            list(BtSnoopHciParser().parse_file(path))

    def test_truncated_packet_data_raises(self, tmp_path: Path) -> None:
        full_record = build_record(
            data=command_packet_data(), received=False, timestamp=datetime.now(tz=UTC)
        )
        truncated = full_record[:-1]  # drop the last data byte
        data = build_file_header() + truncated
        path = _write(tmp_path, "btsnoop_hci.log", data)

        with pytest.raises(ParsingError, match="truncated packet data"):
            list(BtSnoopHciParser().parse_file(path))

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "empty.log", b"")

        with pytest.raises(ParsingError):
            list(BtSnoopHciParser().parse_file(path))
