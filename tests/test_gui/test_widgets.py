"""Tests for the GUI's hex/ASCII formatting and packet table/filter models."""

from __future__ import annotations

import os
import struct
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from revolt_ble_toolkit.analyzers.protocol import ClassifiedPacket, PacketCategory
from revolt_ble_toolkit.gui.widgets import (
    PacketFilterProxyModel,
    PacketTableModel,
    TimelineWidget,
    format_ascii,
    format_hex,
)
from revolt_ble_toolkit.parsers.att import AttOpcode, AttPacket
from revolt_ble_toolkit.parsers.btsnoop.models import PacketDirection

_NOW = datetime(2024, 1, 1, tzinfo=UTC)


@pytest.fixture(scope="module", autouse=True)
def _qapp() -> Iterator[QApplication]:
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    yield app


def _classified(
    hci_number: int,
    opcode: AttOpcode,
    category: PacketCategory,
    *,
    confidence: float = 0.5,
    handle: int = 10,
    value: bytes = b"\x01\x02",
    when: datetime = _NOW,
) -> ClassifiedPacket:
    packet = AttPacket(
        hci_number=hci_number,
        timestamp=when,
        direction=PacketDirection.CONTROLLER_TO_HOST,
        connection_handle=1,
        opcode=opcode,
        parameters=struct.pack("<H", handle) + value,
    )
    return ClassifiedPacket(packet, category, confidence, "test")


def test_format_hex_wraps_every_16_bytes_with_offsets() -> None:
    lines = format_hex(bytes(range(20))).splitlines()
    assert lines[0].startswith("0000")
    assert lines[1].startswith("0010")


def test_format_hex_empty() -> None:
    assert format_hex(b"") == "(empty)"


def test_format_ascii_dots_non_printable_bytes() -> None:
    text = format_ascii(b"\x00\x01A")
    assert "A" in text
    assert "." in text


def test_table_model_dimensions() -> None:
    model = PacketTableModel(
        [_classified(1, AttOpcode.HANDLE_VALUE_NOTIFICATION, PacketCategory.TELEMETRY)],
        handle_uuids={10: "2a19"},
    )
    assert model.rowCount() == 1
    assert model.columnCount() == 10


def test_table_model_resolves_uuid_from_handle() -> None:
    model = PacketTableModel(
        [_classified(1, AttOpcode.HANDLE_VALUE_NOTIFICATION, PacketCategory.TELEMETRY, handle=10)],
        handle_uuids={10: "2a19"},
    )
    index = model.index(0, 6)
    assert model.data(index) == "2a19"


def test_filter_proxy_text_search_matches_any_column() -> None:
    model = PacketTableModel(
        [
            _classified(1, AttOpcode.HANDLE_VALUE_NOTIFICATION, PacketCategory.TELEMETRY),
            _classified(2, AttOpcode.WRITE_REQUEST, PacketCategory.CONFIGURATION),
        ],
        handle_uuids={},
    )
    proxy = PacketFilterProxyModel()
    proxy.setSourceModel(model)

    proxy.setFilterFixedString("WRITE_REQUEST")

    assert proxy.rowCount() == 1


def test_filter_proxy_category_filter() -> None:
    model = PacketTableModel(
        [
            _classified(1, AttOpcode.HANDLE_VALUE_NOTIFICATION, PacketCategory.TELEMETRY),
            _classified(2, AttOpcode.WRITE_REQUEST, PacketCategory.CONFIGURATION),
        ],
        handle_uuids={},
    )
    proxy = PacketFilterProxyModel()
    proxy.setSourceModel(model)

    proxy.set_category_filter("configuration")

    assert proxy.rowCount() == 1


def test_filter_proxy_combines_text_and_category() -> None:
    model = PacketTableModel(
        [
            _classified(1, AttOpcode.WRITE_REQUEST, PacketCategory.CONFIGURATION),
            _classified(2, AttOpcode.WRITE_COMMAND, PacketCategory.CONFIGURATION),
        ],
        handle_uuids={},
    )
    proxy = PacketFilterProxyModel()
    proxy.setSourceModel(model)

    proxy.set_category_filter("configuration")
    proxy.setFilterFixedString("WRITE_COMMAND")

    assert proxy.rowCount() == 1


def test_timeline_buckets_all_packets_and_seeks_to_first_in_bucket() -> None:
    packets = [
        _classified(
            i,
            AttOpcode.HANDLE_VALUE_NOTIFICATION,
            PacketCategory.TELEMETRY,
            when=_NOW + timedelta(seconds=i),
        )
        for i in range(5)
    ]

    timeline = TimelineWidget()
    timeline.resize(800, 60)
    timeline.set_packets(packets)

    assert sum(timeline._counts) == len(packets)
    assert all(0 <= idx < len(packets) for idx in timeline._first_index_by_bucket)


def test_timeline_handles_single_packet_without_dividing_by_zero() -> None:
    timeline = TimelineWidget()
    timeline.set_packets([_classified(1, AttOpcode.READ_RESPONSE, PacketCategory.UNKNOWN)])

    assert sum(timeline._counts) == 1


def test_timeline_handles_empty_input() -> None:
    timeline = TimelineWidget()
    timeline.set_packets([])

    assert timeline._counts == []
