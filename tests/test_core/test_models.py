"""Tests for core domain models."""

from __future__ import annotations

from pathlib import Path

from revolt_ble_toolkit.core.enums import CaptureFormat
from revolt_ble_toolkit.core.models import CaptureFile


def test_capture_file_defaults() -> None:
    capture = CaptureFile(path=Path("sample.cfa"))
    assert capture.format is CaptureFormat.UNKNOWN
    assert capture.size_bytes == 0
    assert capture.discovered_at is None
