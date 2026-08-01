"""Core domain models.

These dataclasses describe the shapes that will flow between the parsing,
analysis, and export layers. They intentionally hold no behaviour yet -
concrete parsing/analysis logic arrives in a later milestone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from revolt_ble_toolkit.core.enums import CaptureFormat


@dataclass(frozen=True, slots=True)
class CaptureFile:
    """Metadata describing a capture log on disk."""

    path: Path
    format: CaptureFormat = CaptureFormat.UNKNOWN
    size_bytes: int = 0
    discovered_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ParsedRecord:
    """A single, format-agnostic record extracted from a capture file."""

    index: int
    timestamp: datetime | None
    raw_payload: bytes
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Aggregated output produced by an analyzer for a set of records."""

    summary: dict[str, Any] = field(default_factory=dict)
    findings: tuple[str, ...] = field(default_factory=tuple)
