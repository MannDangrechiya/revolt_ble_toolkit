"""Main window: drag-and-drop capture loading, packet table + filters/search,
timeline scrubber, and hex/ASCII/statistics panes for the selected packet.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QTableView,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from revolt_ble_toolkit.analyzers.gatt import handle_uuid_map
from revolt_ble_toolkit.analyzers.protocol import PacketCategory
from revolt_ble_toolkit.core.exceptions import ToolkitError
from revolt_ble_toolkit.exporters.capture_report import build_statistics, run_pipeline
from revolt_ble_toolkit.gui.widgets import (
    PacketFilterProxyModel,
    PacketTableModel,
    TimelineWidget,
    format_ascii,
    format_hex,
)


def _monospace_font() -> QFont:
    font = QFont("Consolas")
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


class MainWindow(QMainWindow):
    """Top-level window. Load a capture via drag-and-drop or File > Open."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Revolt BLE Toolkit")
        self.resize(1200, 800)
        self.setAcceptDrops(True)

        self._model: PacketTableModel | None = None
        self._proxy = PacketFilterProxyModel(self)

        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file_dialog)
        toolbar.addAction(open_action)

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
