"""Smoke tests for MainWindow.load_capture, end to end with a synthetic capture."""

from __future__ import annotations

import os
import struct
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from revolt_ble_toolkit.gui.main_window import MainWindow
from tests.test_parsers.fixtures import acl_packet_data, build_file_header, build_record

_ATT_CID = 0x0004


@pytest.fixture(scope="module", autouse=True)
def _qapp() -> Iterator[QApplication]:
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    yield app


def _write_btsnoop(path: Path) -> None:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    att_pdu = bytes([0x1B]) + struct.pack("<H", 20) + b"\x64"  # Handle Value Notification
    l2cap = struct.pack("<HH", len(att_pdu), _ATT_CID) + att_pdu
    data = build_file_header()
    data += build_record(
        data=acl_packet_data(connection_handle=1, payload=l2cap), received=True, timestamp=now
    )
    path.write_bytes(data)


def test_load_capture_populates_table(tmp_path: Path) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    _write_btsnoop(btsnoop_path)
    window = MainWindow()

    window.load_capture(btsnoop_path)

    assert window._model is not None
    assert window._model.rowCount() == 1
    assert "1 HCI packets" in window.statusBar().currentMessage()


def test_load_capture_bad_file_shows_error_not_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad_path = tmp_path / "not_a_capture.log"
    bad_path.write_bytes(b"garbage")
    window = MainWindow()
    shown: dict[str, bool] = {}
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.QMessageBox.critical",
        lambda *a, **k: shown.setdefault("called", True),
    )

    window.load_capture(bad_path)

    assert shown.get("called") is True
    assert window._model is None
