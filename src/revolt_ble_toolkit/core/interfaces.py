"""Abstract contracts implemented by concrete parsers, analyzers, and exporters.

Defined with :class:`typing.Protocol` for structural typing: implementations
do not need to inherit from these types explicitly, they only need to
satisfy the method signatures (Interface Segregation, Dependency Inversion).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from revolt_ble_toolkit.core.models import AnalysisResult, CaptureFile, ParsedRecord


@runtime_checkable
class LogParser(Protocol):
    """Parses a capture file into a stream of format-agnostic records."""

    def supports(self, capture: CaptureFile) -> bool:
        """Return True if this parser can handle the given capture file."""
        ...

    def parse(self, capture: CaptureFile) -> Iterator[ParsedRecord]:
        """Yield parsed records from the capture file."""
        ...


@runtime_checkable
class PacketAnalyzer(Protocol):
    """Analyzes a stream of parsed records and produces a result."""

    def analyze(self, records: Iterable[ParsedRecord]) -> AnalysisResult:
        """Return an aggregated analysis result for the given records."""
        ...


@runtime_checkable
class ResultExporter(Protocol):
    """Exports an analysis result to a destination."""

    def export(self, result: AnalysisResult, destination: Path) -> None:
        """Write the analysis result to the destination path."""
        ...
