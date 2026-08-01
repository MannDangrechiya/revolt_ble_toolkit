"""Main window: drag-and-drop capture loading, packet table + filters/search,
timeline scrubber, and hex/ASCII/statistics panes for the selected packet.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QTableView,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from revolt_ble_toolkit.analyzers.compare import compare_captures, format_diff_report
from revolt_ble_toolkit.analyzers.gatt import handle_uuid_map
from revolt_ble_toolkit.analyzers.protocol import PacketCategory
from revolt_ble_toolkit.core.exceptions import ToolkitError
from revolt_ble_toolkit.exporters.capture_report import (
    build_statistics,
    generate_capture_report,
    run_pipeline,
)
from revolt_ble_toolkit.gui.widgets import (
    PacketFilterProxyModel,
    PacketTableModel,
    TimelineWidget,
    format_ascii,
    format_hex,
)

_MAX_RECENT_CAPTURES = 5
_SETTINGS_RECENT_KEY = "recentCaptures"


def _monospace_font() -> QFont:
    font = QFont("Consolas")
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


class MainWindow(QMainWindow):
    """Top-level window. Load a capture via drag-and-drop or File > Open."""

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Revolt BLE Toolkit")
        self.resize(1200, 800)
        self.setAcceptDrops(True)

        self._settings = settings if settings is not None else QSettings("RevoltBleToolkit", "GUI")
        self._model: PacketTableModel | None = None
        self._proxy = PacketFilterProxyModel(self)
        self._current_path: Path | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file_dialog)
        toolbar.addAction(open_action)

        self.export_action = QAction("Export Report...", self)
        self.export_action.setShortcut("Ctrl+E")
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(self._export_report)

        self.compare_action = QAction("Compare with...", self)
        self.compare_action.setShortcut("Ctrl+Shift+C")
        self.compare_action.setEnabled(False)
        self.compare_action.triggered.connect(self._compare_with)

        focus_search_action = QAction("Focus Search", self)
        focus_search_action.setShortcut("Ctrl+F")
        focus_search_action.triggered.connect(self._focus_search)
        self.addAction(focus_search_action)

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(open_action)
        self.recent_menu = QMenu("Recent Captures", self)
        file_menu.addMenu(self.recent_menu)
        file_menu.addSeparator()
        file_menu.addAction(self.export_action)
        file_menu.addAction(self.compare_action)
        file_menu.addSeparator()
        file_menu.addAction(quit_action)
        self._rebuild_recent_menu()

        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(focus_search_action)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._proxy.setFilterFixedString)
        toolbar.addWidget(self.search_box)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All categories", None)
        for category in PacketCategory:
            self.category_filter.addItem(category.value, category.value)
        self.category_filter.currentIndexChanged.connect(self._on_category_changed)
        toolbar.addWidget(self.category_filter)

        self.timeline = TimelineWidget()
        self.timeline.bucket_clicked.connect(self._seek_to_index)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        mono_font = _monospace_font()
        self.hex_view = QPlainTextEdit()
        self.hex_view.setReadOnly(True)
        self.hex_view.setFont(mono_font)
        self.ascii_view = QPlainTextEdit()
        self.ascii_view.setReadOnly(True)
        self.ascii_view.setFont(mono_font)
        self.stats_view = QPlainTextEdit()
        self.stats_view.setReadOnly(True)
        self.stats_view.setFont(mono_font)

        tabs = QTabWidget()
        tabs.addTab(self.hex_view, "Hex")
        tabs.addTab(self.ascii_view, "ASCII")
        tabs.addTab(self.stats_view, "Statistics")

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self.table)
        self._splitter.addWidget(tabs)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)
        self._splitter.hide()

        central = QWidget()
        layout = QVBoxLayout(central)
        self.placeholder = QLabel("Drag & drop a btsnoop_hci.log file here, or File > Open...")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder)
        layout.addWidget(self.timeline)
        layout.addWidget(self._splitter)
        self.setCentralWidget(central)
        self.timeline.hide()

        self.statusBar().showMessage("No capture loaded")

    # --- drag and drop -------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            self.load_capture(Path(urls[0].toLocalFile()))

    def _open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open BTSnoop capture", "", "BTSnoop log (*.log);;All files (*)"
        )
        if path:
            self.load_capture(Path(path))

    def _focus_search(self) -> None:
        self.search_box.setFocus()
        self.search_box.selectAll()

    # --- recent captures -------------------------------------------------------

    def _recent_paths(self) -> list[str]:
        value = self._settings.value(_SETTINGS_RECENT_KEY, [])
        if isinstance(value, str):  # QSettings collapses a single-item list to a bare str
            return [value]
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]

    def _remember_recent_path(self, path: Path) -> None:
        paths = [p for p in self._recent_paths() if p != str(path)]
        paths.insert(0, str(path))
        self._settings.setValue(_SETTINGS_RECENT_KEY, paths[:_MAX_RECENT_CAPTURES])
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self) -> None:
        self.recent_menu.clear()
        paths = self._recent_paths()
        if not paths:
            empty_action = self.recent_menu.addAction("(no recent captures)")
            empty_action.setEnabled(False)
            return
        for path_str in paths:
            action = self.recent_menu.addAction(path_str)
            action.triggered.connect(lambda checked=False, p=path_str: self.load_capture(Path(p)))

    # --- export / compare --------------------------------------------------------

    def _export_report(self) -> None:
        if self._current_path is None:
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Select export directory")
        if not out_dir:
            return
        try:
            paths = generate_capture_report(self._current_path, Path(out_dir))
        except (ToolkitError, OSError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(
            self,
            "Export complete",
            "Wrote:\n"
            f"{paths.commands_csv}\n{paths.notifications_csv}\n"
            f"{paths.statistics_json}\n{paths.summary_md}",
        )

    def _compare_with(self) -> None:
        if self._current_path is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Compare with capture", "", "BTSnoop log (*.log);;All files (*)"
        )
        if not path:
            return
        try:
            diffs = compare_captures(self._current_path, Path(path))
        except (ToolkitError, OSError) as exc:
            QMessageBox.critical(self, "Compare failed", str(exc))
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Compare with {Path(path).name}")
        dialog.resize(640, 420)
        layout = QVBoxLayout(dialog)
        report_view = QPlainTextEdit()
        report_view.setReadOnly(True)
        report_view.setFont(_monospace_font())
        report_view.setPlainText(format_diff_report(diffs))
        layout.addWidget(report_view)
        dialog.exec()

    # --- loading ---------------------------------------------------------------

    def load_capture(self, path: Path) -> None:
        """Parse ``path`` and populate the table, timeline, and statistics panes."""
        try:
            result = run_pipeline(path)
        except (ToolkitError, OSError) as exc:
            QMessageBox.critical(self, "Failed to load capture", str(exc))
            return

        handle_uuids = handle_uuid_map(result.services)
        self._model = PacketTableModel(result.classified, handle_uuids)
        self._proxy.setSourceModel(self._model)
        self.timeline.set_packets(result.classified)
        self.stats_view.setPlainText(json.dumps(build_statistics(path, result), indent=2))
        self.hex_view.clear()
        self.ascii_view.clear()

        self._current_path = path
        self.export_action.setEnabled(True)
        self.compare_action.setEnabled(True)
        self._remember_recent_path(path)

        self.placeholder.hide()
        self.timeline.show()
        self._splitter.show()
        self.statusBar().showMessage(
            f"{path.name} — {len(result.hci_packets)} HCI packets, "
            f"{len(result.att_packets)} ATT packets"
        )

    def _on_category_changed(self) -> None:
        self._proxy.set_category_filter(self.category_filter.currentData())

    def _on_selection_changed(self) -> None:
        if self._model is None:
            return
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return
        source_index = self._proxy.mapToSource(indexes[0])
        packet = self._model.packet_at(source_index.row())
        self.hex_view.setPlainText(format_hex(packet.packet.value))
        self.ascii_view.setPlainText(format_ascii(packet.packet.value))

    def _seek_to_index(self, index: int) -> None:
        if self._model is None:
            return
        proxy_index = self._proxy.mapFromSource(self._model.index(index, 0))
        if proxy_index.isValid():
            self.table.selectRow(proxy_index.row())
            self.table.scrollTo(proxy_index)
