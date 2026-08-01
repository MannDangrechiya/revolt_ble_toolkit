"""Packet table model, search/category filter, hex/ASCII formatting, and the
timeline scrubber widget used by the main window.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from revolt_ble_toolkit.analyzers.protocol import ClassifiedPacket
from revolt_ble_toolkit.parsers.btsnoop.models import PacketDirection

_COLUMNS = ["#", "Time", "Dir", "Conn", "Opcode", "Handle", "UUID", "Category", "Conf.", "Size"]
_ROOT_INDEX = QModelIndex()


def format_hex(data: bytes, width: int = 16) -> str:
    """Space-separated hex bytes, one offset-prefixed line per ``width`` bytes."""
    if not data:
        return "(empty)"
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i : i + width]
        lines.append(f"{i:04X}  " + " ".join(f"{b:02X}" for b in chunk))
    return "\n".join(lines)


def format_ascii(data: bytes, width: int = 16) -> str:
    """Printable-or-dot ASCII representation, one offset-prefixed line per ``width`` bytes."""
    if not data:
        return "(empty)"
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i : i + width]
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{i:04X}  {text}")
    return "\n".join(lines)


class PacketTableModel(QAbstractTableModel):
    """Read-only table over a list of classified ATT packets."""

    def __init__(
        self,
        packets: Sequence[ClassifiedPacket],
        handle_uuids: dict[int, str],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._packets = list(packets)
        self._handle_uuids = handle_uuids

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _ROOT_INDEX) -> int:
        return 0 if parent.isValid() else len(self._packets)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = _ROOT_INDEX) -> int:
        return 0 if parent.isValid() else len(_COLUMNS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        return _COLUMNS[section]

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        att = self._packets[index.row()].packet
        category = self._packets[index.row()].category
        confidence = self._packets[index.row()].confidence
        handle = att.attribute_handle
        column = _COLUMNS[index.column()]
        if column == "#":
            return att.hci_number
        if column == "Time":
            return att.timestamp.strftime("%H:%M:%S.%f")[:-3]
        if column == "Dir":
            return "RX" if att.direction is PacketDirection.CONTROLLER_TO_HOST else "TX"
        if column == "Conn":
            return att.connection_handle
        if column == "Opcode":
            return att.opcode.name
        if column == "Handle":
            return handle if handle is not None else ""
        if column == "UUID":
            return self._handle_uuids.get(handle, "") if handle is not None else ""
        if column == "Category":
            return category.value
        if column == "Conf.":
            return f"{confidence:.2f}"
        if column == "Size":
            return len(att.value)
        return None

    def packet_at(self, row: int) -> ClassifiedPacket:
        return self._packets[row]


class PacketFilterProxyModel(QSortFilterProxyModel):
    """Free-text search across all columns, plus an optional exact category filter."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.setFilterKeyColumn(-1)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._category: str | None = None

    def set_category_filter(self, category: str | None) -> None:
        self._category = category
        self.invalidate()

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex | QPersistentModelIndex
    ) -> bool:
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        if self._category is None:
            return True
        model = self.sourceModel()
        index = model.index(source_row, _COLUMNS.index("Category"), source_parent)
        return bool(model.data(index) == self._category)


class TimelineWidget(QWidget):
    """Click-to-seek packet-density histogram over the loaded capture's time range."""

    bucket_clicked = Signal(int)  # index of the first packet falling in the clicked bucket

    _BUCKETS = 80

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(50)
        self.setMaximumHeight(70)
        self._counts: list[int] = []
        self._first_index_by_bucket: list[int] = []

    def set_packets(self, packets: Sequence[ClassifiedPacket]) -> None:
        if not packets:
            self._counts = []
            self._first_index_by_bucket = []
            self.update()
            return

        times = [p.packet.timestamp.timestamp() for p in packets]
        start, span = times[0], (times[-1] - times[0]) or 1.0
        counts = [0] * self._BUCKETS
        first_index = [-1] * self._BUCKETS
        for i, t in enumerate(times):
            bucket = min(self._BUCKETS - 1, int((t - start) / span * self._BUCKETS))
            counts[bucket] += 1
            if first_index[bucket] == -1:
                first_index[bucket] = i

        # ponytail: empty buckets fall back to the previous bucket's packet so
        # clicking anywhere still seeks somewhere sensible.
        last = 0
        for i in range(self._BUCKETS):
            if first_index[i] == -1:
                first_index[i] = last
            else:
                last = first_index[i]

        self._counts = counts
        self._first_index_by_bucket = first_index
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().base())
        if self._counts:
            bucket_width = self.width() / len(self._counts)
            max_count = max(self._counts) or 1
            for i, count in enumerate(self._counts):
                bar_height = int((count / max_count) * (self.height() - 4))
                x = int(i * bucket_width)
                painter.fillRect(
                    x,
                    self.height() - bar_height,
                    max(1, int(bucket_width) - 1),
                    bar_height,
                    self.palette().highlight(),
                )
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._counts:
            return
        fraction = event.position().x() / self.width()
        bucket = min(len(self._counts) - 1, max(0, int(fraction * len(self._counts))))
        self.bucket_clicked.emit(self._first_index_by_bucket[bucket])
