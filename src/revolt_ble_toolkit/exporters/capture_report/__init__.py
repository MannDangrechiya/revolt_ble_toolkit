"""Generates commands.csv, notifications.csv, statistics.json, and summary.md
from a BTSnoop capture, by running the parse -> ATT -> GATT -> protocol
classification pipeline end to end.
"""

from __future__ import annotations

from revolt_ble_toolkit.exporters.capture_report.report import (
    CaptureReportPaths,
    generate_capture_report,
)

__all__ = ["CaptureReportPaths", "generate_capture_report"]
