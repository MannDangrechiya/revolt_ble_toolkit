"""Analysis result exporters.

``BaseExporter`` is the generic extension point for future pipeline
integration; ``generate_capture_report`` is the concrete, standalone
exporter that writes commands.csv/notifications.csv/statistics.json/summary.md.
"""

from __future__ import annotations

from revolt_ble_toolkit.exporters.base import BaseExporter
from revolt_ble_toolkit.exporters.capture_report import (
    CaptureReportPaths,
    PipelineResult,
    build_statistics,
    generate_capture_report,
    run_pipeline,
)

__all__ = [
    "BaseExporter",
    "CaptureReportPaths",
    "PipelineResult",
    "build_statistics",
    "generate_capture_report",
    "run_pipeline",
]
