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

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from revolt_ble_toolkit.gui.main_window import _SETTINGS_RECENT_KEY, MainWindow
from tests.test_parsers.fixtures import acl_packet_data, build_file_header, build_record

_ATT_CID = 0x0004


@pytest.fixture(scope="module", autouse=True)
def _qapp() -> Iterator[QApplication]:
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    yield app


def _make_window(tmp_path: Path) -> MainWindow:
    # ponytail: an isolated ini-backed QSettings so tests never touch the
    # real user registry/preferences for the "recent captures" list.
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    return MainWindow(settings=settings)


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
    window = _make_window(tmp_path)

    window.load_capture(btsnoop_path)

    assert window._model is not None
    assert window._model.rowCount() == 1
    assert "1 HCI packets" in window.statusBar().currentMessage()


def test_load_capture_bad_file_shows_error_not_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad_path = tmp_path / "not_a_capture.log"
    bad_path.write_bytes(b"garbage")
    window = _make_window(tmp_path)
    shown: dict[str, bool] = {}
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.QMessageBox.critical",
        lambda *a, **k: shown.setdefault("called", True),
    )

    window.load_capture(bad_path)

    assert shown.get("called") is True
    assert window._model is None


def test_export_and_compare_actions_disabled_until_capture_loaded(tmp_path: Path) -> None:
    window = _make_window(tmp_path)

    assert window.export_action.isEnabled() is False
    assert window.compare_action.isEnabled() is False

    _write_btsnoop(tmp_path / "btsnoop_hci.log")
    window.load_capture(tmp_path / "btsnoop_hci.log")

    assert window.export_action.isEnabled() is True
    assert window.compare_action.isEnabled() is True


def test_category_filter_hides_non_matching_rows(tmp_path: Path) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    _write_btsnoop(btsnoop_path)
    window = _make_window(tmp_path)
    window.load_capture(btsnoop_path)
    actual_category = window._model.packet_at(0).category.value  # type: ignore[union-attr]

    matching_index = window.category_filter.findData(actual_category)
    window.category_filter.setCurrentIndex(matching_index)
    assert window._proxy.rowCount() == 1

    other_category = next(
        window.category_filter.itemData(i)
        for i in range(window.category_filter.count())
        if window.category_filter.itemData(i) not in (None, actual_category)
    )
    window.category_filter.setCurrentIndex(window.category_filter.findData(other_category))
    assert window._proxy.rowCount() == 0


def test_selecting_row_populates_hex_and_ascii_views(tmp_path: Path) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    _write_btsnoop(btsnoop_path)
    window = _make_window(tmp_path)
    window.load_capture(btsnoop_path)

    window.table.selectRow(0)

    assert "64" in window.hex_view.toPlainText()  # the packet's single value byte, 0x64
    assert window.ascii_view.toPlainText() != ""


def test_seek_to_index_selects_the_target_row(tmp_path: Path) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    _write_btsnoop(btsnoop_path)
    window = _make_window(tmp_path)
    window.load_capture(btsnoop_path)

    window._seek_to_index(0)

    selected = window.table.selectionModel().selectedRows()
    assert len(selected) == 1
    assert selected[0].row() == 0


def test_recent_paths_ignores_unexpected_settings_value_shape(tmp_path: Path) -> None:
    window = _make_window(tmp_path)
    window._settings.setValue(_SETTINGS_RECENT_KEY, 42)  # not a str or list — malformed value

    assert window._recent_paths() == []


def test_recent_paths_handles_single_entry_collapsed_to_bare_string(tmp_path: Path) -> None:
    window = _make_window(tmp_path)
    # QSettings' ini backend collapses a single-item list back to a bare str on read.
    window._settings.setValue(_SETTINGS_RECENT_KEY, "only_one.log")

    assert window._recent_paths() == ["only_one.log"]


def test_load_capture_adds_to_recent_menu(tmp_path: Path) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    _write_btsnoop(btsnoop_path)
    window = _make_window(tmp_path)

    window.load_capture(btsnoop_path)

    recent_actions = [a.text() for a in window.recent_menu.actions()]
    assert str(btsnoop_path) in recent_actions


def test_recent_menu_reloads_capture_when_clicked(tmp_path: Path) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    _write_btsnoop(btsnoop_path)
    window = _make_window(tmp_path)
    window.load_capture(btsnoop_path)
    window._model = None  # force a fresh reload to prove the action re-triggers it

    (action,) = [a for a in window.recent_menu.actions() if a.text() == str(btsnoop_path)]
    action.trigger()

    assert window._model is not None


def test_recent_menu_caps_at_five_and_moves_reopened_file_to_front(tmp_path: Path) -> None:
    window = _make_window(tmp_path)
    paths = []
    for i in range(6):
        p = tmp_path / f"capture_{i}.log"
        _write_btsnoop(p)
        paths.append(p)
        window.load_capture(p)

    recent = window._recent_paths()
    assert len(recent) == 5
    assert str(paths[0]) not in recent  # oldest of the 6 loads, evicted by the cap
    assert recent[0] == str(paths[-1])  # most recently loaded is first

    window.load_capture(paths[3])  # reopen a capture already in the list
    recent = window._recent_paths()
    assert recent[0] == str(paths[3])


def test_export_report_writes_files_and_shows_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    _write_btsnoop(btsnoop_path)
    out_dir = tmp_path / "out"
    window = _make_window(tmp_path)
    window.load_capture(btsnoop_path)
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.QFileDialog.getExistingDirectory",
        lambda *a, **k: str(out_dir),
    )
    shown: dict[str, bool] = {}
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.QMessageBox.information",
        lambda *a, **k: shown.setdefault("called", True),
    )

    window._export_report()

    assert shown.get("called") is True
    assert (out_dir / "commands.csv").exists()
    assert (out_dir / "notifications.csv").exists()
    assert (out_dir / "statistics.json").exists()
    assert (out_dir / "summary.md").exists()


def test_compare_with_shows_dialog_with_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path1 = tmp_path / "before.log"
    path2 = tmp_path / "after.log"
    _write_btsnoop(path1)
    _write_btsnoop(path2)
    window = _make_window(tmp_path)
    window.load_capture(path1)
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(path2), ""),
    )
    shown: dict[str, object] = {}

    def _fake_exec(self: object) -> int:
        shown["called"] = True
        return 0

    monkeypatch.setattr("revolt_ble_toolkit.gui.main_window.QDialog.exec", _fake_exec)

    window._compare_with()

    assert shown.get("called") is True


def test_export_report_noop_without_loaded_capture(tmp_path: Path) -> None:
    window = _make_window(tmp_path)  # no load_capture call: _current_path is None

    window._export_report()  # must not raise despite no capture loaded


def test_export_report_cancelled_dialog_does_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    _write_btsnoop(btsnoop_path)
    window = _make_window(tmp_path)
    window.load_capture(btsnoop_path)
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.QFileDialog.getExistingDirectory",
        lambda *a, **k: "",
    )

    window._export_report()  # user cancelled the directory picker: no crash, no files


def test_export_report_shows_error_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    _write_btsnoop(btsnoop_path)
    window = _make_window(tmp_path)
    window.load_capture(btsnoop_path)
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.QFileDialog.getExistingDirectory",
        lambda *a, **k: str(tmp_path / "out"),
    )
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.generate_capture_report",
        lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")),
    )
    shown: dict[str, bool] = {}
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.QMessageBox.critical",
        lambda *a, **k: shown.setdefault("called", True),
    )

    window._export_report()

    assert shown.get("called") is True


def test_compare_with_noop_without_loaded_capture(tmp_path: Path) -> None:
    window = _make_window(tmp_path)  # no load_capture call: _current_path is None

    window._compare_with()  # must not raise despite no capture loaded


def test_compare_with_cancelled_dialog_does_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    btsnoop_path = tmp_path / "btsnoop_hci.log"
    _write_btsnoop(btsnoop_path)
    window = _make_window(tmp_path)
    window.load_capture(btsnoop_path)
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: ("", ""),
    )

    window._compare_with()  # user cancelled the file picker: no crash, no dialog


def test_compare_with_shows_error_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path1 = tmp_path / "before.log"
    path2 = tmp_path / "after.log"
    _write_btsnoop(path1)
    _write_btsnoop(path2)
    window = _make_window(tmp_path)
    window.load_capture(path1)
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(path2), ""),
    )
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.compare_captures",
        lambda *a, **k: (_ for _ in ()).throw(OSError("bad file")),
    )
    shown: dict[str, bool] = {}
    monkeypatch.setattr(
        "revolt_ble_toolkit.gui.main_window.QMessageBox.critical",
        lambda *a, **k: shown.setdefault("called", True),
    )

    window._compare_with()

    assert shown.get("called") is True


def test_focus_search_moves_focus_to_search_box(tmp_path: Path) -> None:
    window = _make_window(tmp_path)
    window.show()
    QApplication.processEvents()

    window._focus_search()
    QApplication.processEvents()

    assert QApplication.focusWidget() is window.search_box
    window.hide()
