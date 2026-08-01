"""Core domain layer: interfaces, models, enums, and exceptions.

This package defines the abstractions the rest of the toolkit depends on.
Concrete parsers, analyzers, and exporters implement these contracts rather
than the core depending on them (Dependency Inversion Principle).
"""

from __future__ import annotations

from revolt_ble_toolkit.core.enums import CaptureFormat, TransportType
from revolt_ble_toolkit.core.exceptions import (
    AnalysisError,
    ConfigurationError,
    ExportError,
    ParsingError,
    ToolkitError,
)
from revolt_ble_toolkit.core.interfaces import LogParser, PacketAnalyzer, ResultExporter
from revolt_ble_toolkit.core.models import AnalysisResult, CaptureFile, ParsedRecord

__all__ = [
    "AnalysisError",
    "AnalysisResult",
    "CaptureFile",
    "CaptureFormat",
    "ConfigurationError",
    "ExportError",
    "LogParser",
    "PacketAnalyzer",
    "ParsedRecord",
    "ParsingError",
    "ResultExporter",
    "ToolkitError",
    "TransportType",
]
