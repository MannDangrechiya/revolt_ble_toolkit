"""Cross-capture comparator: diffs notified values by GATT handle between two
captures and heuristically correlates changes to a physical quantity.
"""

from __future__ import annotations

from revolt_ble_toolkit.analyzers.compare.analyzer import (
    CaptureComparator,
    compare_captures,
    format_diff_report,
)
from revolt_ble_toolkit.analyzers.compare.models import CorrelationCategory, HandleDiff

__all__ = [
    "CaptureComparator",
    "CorrelationCategory",
    "HandleDiff",
    "compare_captures",
    "format_diff_report",
]
