"""Tests for the `revolt-ble-toolkit` CLI (parse/analyze/export/compare)."""

from __future__ import annotations

import struct
from datetime import UTC, datetime
from pathlib import Path

import pytest

from revolt_ble_toolkit.cli.main import main
from tests.test_parsers.fixtures import acl_packet_data, build_file_header, build_record

_ATT_CID = 0x0004
_NOW = datetime(2024, 1, 1, tzinfo=UTC)


def _att_l2cap(opcode: int, handle: int, value: bytes = b"") -> bytes:
    att_pdu = bytes([opcode]) + struct.pack("<H", handle) + value
    return struct.pack("<HH", len(att_pdu), _ATT_CID) + att_pdu


def _write_capture(path: Path, notify_value: bytes = b"\x64") -> None:
    data = build_file_header()
    data += build_record(
        data=acl_packet_data(connection_handle=1, payload=_att_l2cap(0x1B, 20, notify_value)),
        received=True,
        timestamp=_NOW,
    )
    path.write_bytes(data)


def test_parse_command_prints_packet_counts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    capture = tmp_path / "btsnoop_hci.log"
    _write_capture(capture)

    exit_code = main(["parse", str(capture)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "1 HCI packets" in out
    assert "ACL_DATA: 1" in out
    assert "connection handles: [1]" in out


def test_analyze_command_prints_stats_and_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    capture = tmp_path / "btsnoop_hci.log"
    _write_capture(capture)

    exit_code = main(["analyze", str(capture)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert '"total_packets": 1' in out
    assert "HANDLE_VALUE_NOTIFICATION" in out
    assert "Protocol Analysis Report" in out


def test_export_command_writes_four_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    capture = tmp_path / "btsnoop_hci.log"
    _write_capture(capture)
    out_dir = tmp_path / "out"

    exit_code = main(["export", str(capture), "--out-dir", str(out_dir)])

    assert exit_code == 0
    assert (out_dir / "commands.csv").exists()
    assert (out_dir / "notifications.csv").exists()
    assert (out_dir / "statistics.json").exists()
    assert (out_dir / "summary.md").exists()
    out = capsys.readouterr().out
    assert str(out_dir / "summary.md") in out


def test_compare_command_reports_no_diffs_for_identical_captures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    capture = tmp_path / "btsnoop_hci.log"
    _write_capture(capture)

    exit_code = main(["compare", str(capture), str(capture)])

    assert exit_code == 0
    assert "No changed handles detected" in capsys.readouterr().out


def test_compare_command_reports_a_changed_handle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    capture1 = tmp_path / "before.log"
    capture2 = tmp_path / "after.log"
    _write_capture(capture1, notify_value=b"\x50")  # 80
    _write_capture(capture2, notify_value=b"\x32")  # 50

    exit_code = main(["compare", str(capture1), str(capture2)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "handle 20" in out
    assert "before: 50" in out
    assert "after:  32" in out


def test_missing_file_returns_exit_code_1_with_clean_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["parse", str(tmp_path / "does_not_exist.log")])

    assert exit_code == 1
    assert "Error:" in capsys.readouterr().err


def test_no_command_prints_help_and_returns_0(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])

    assert exit_code == 0
    assert "usage:" in capsys.readouterr().out


def test_version_flag_exits_cleanly() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
