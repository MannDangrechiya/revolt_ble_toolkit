"""Tests for the capture report exporter (commands/notifications/stats/summary)."""

from __future__ import annotations

import json
import struct
from datetime import UTC, datetime
from pathlib import Path

import pytest

from revolt_ble_toolkit.core.exceptions import ExportError
from revolt_ble_toolkit.exporters.capture_report import generate_capture_report
from tests.test_parsers.fixtures import acl_packet_data, build_file_header, build_record

_ATT_CID = 0x0004


def _att_l2cap(opcode: int, handle: int, value: bytes = b"") -> bytes:
    att_pdu = bytes([opcode]) + struct.pack("<H", handle) + value
    return struct.pack("<HH", len(att_pdu), _ATT_CID) + att_pdu


def _write_btsnoop(path: Path) -> None:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    data = build_file_header()
    data += build_record(
        data=acl_packet_data(connection_handle=1, payload=_att_l2cap(0x52, 10, b"\x01")),
        received=False,
        timestamp=now,
    )
    data += build_record(
        data=acl_packet_data(connection_handle=1, payload=_att_l2cap(0x1B, 20, b"\x64")),
        received=True,
        timestamp=now,
    )
    path.write_bytes(data)


def test_generate_capture_report_writes_four_files(tmp_path: Path) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    _write_btsnoop(btsnoop_path)

    paths = generate_capture_report(btsnoop_path, tmp_path / "out")

    assert paths.commands_csv.exists()
    assert paths.notifications_csv.exists()
    assert paths.statistics_json.exists()
    assert paths.summary_md.exists()

    commands_rows = paths.commands_csv.read_text().splitlines()
    assert len(commands_rows) == 2  # header + 1 write command
    assert "10" in commands_rows[1] and "01" in commands_rows[1]

    notification_rows = paths.notifications_csv.read_text().splitlines()
    assert len(notification_rows) == 2  # header + 1 notification
    assert "20" in notification_rows[1] and "64" in notification_rows[1]

    stats = json.loads(paths.statistics_json.read_text())
    assert stats["hci"]["total_packets"] == 2
    assert stats["att"]["total_packets"] == 2
    assert stats["att"]["by_opcode"]["WRITE_COMMAND"] == 1
    assert stats["att"]["by_opcode"]["HANDLE_VALUE_NOTIFICATION"] == 1

    summary = paths.summary_md.read_text()
    assert "# Capture Summary" in summary
    assert "HCI packets: 2" in summary


def test_generate_capture_report_handles_no_att_traffic(tmp_path: Path) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    btsnoop_path.write_bytes(build_file_header())  # header only, zero records

    paths = generate_capture_report(btsnoop_path, tmp_path / "out")

    assert paths.commands_csv.read_text().splitlines() == [
        "hci_number,timestamp,connection_handle,attribute_handle,uuid,value_hex,value_length"
    ]
    stats = json.loads(paths.statistics_json.read_text())
    assert stats["hci"]["total_packets"] == 0
    assert stats["protocol_classification"] == {}
    assert "No GATT discovery PDUs" in paths.summary_md.read_text()


def test_generate_capture_report_summary_lists_discovered_services(tmp_path: Path) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    now = datetime(2024, 1, 1, tzinfo=UTC)
    # Read By Group Type Response (0x11): opcode + entry_length + (start, end, uuid16) entries
    # — no handle-prefix, unlike the write/notify PDUs _att_l2cap() builds.
    att_pdu = bytes([0x11, 6]) + struct.pack("<HHH", 1, 5, 0x1800)  # Generic Access
    l2cap = struct.pack("<HH", len(att_pdu), _ATT_CID) + att_pdu
    data = build_file_header()
    data += build_record(
        data=acl_packet_data(connection_handle=1, payload=l2cap),
        received=True,
        timestamp=now,
    )
    btsnoop_path.write_bytes(data)

    paths = generate_capture_report(btsnoop_path, tmp_path / "out")

    summary = paths.summary_md.read_text()
    assert "| Service UUID | Handles | Characteristics |" in summary
    assert "`1800`" in summary
    assert "1-5" in summary


def test_generate_capture_report_wraps_oserror_as_export_error(tmp_path: Path) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    btsnoop_path.write_bytes(build_file_header())
    blocked_out_dir = tmp_path / "blocked"
    blocked_out_dir.write_text("occupies the path so mkdir() fails", encoding="utf-8")

    with pytest.raises(ExportError, match="Failed to write report"):
        generate_capture_report(btsnoop_path, blocked_out_dir)
