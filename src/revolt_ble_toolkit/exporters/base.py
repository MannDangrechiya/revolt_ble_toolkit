"""Base class for concrete result exporters.

Concrete exporters (added in a future milestone) subclass :class:`BaseExporter`
and implement :meth:`export`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.core.models import AnalysisResult

logger = get_logger(__name__)


class BaseExporter(ABC):
    """Common scaffolding shared by all exporter implementations."""

    @abstractmethod
    def export(self, result: AnalysisResult, destination: Path) -> None:
        """Write the analysis result to the destination path."""
        raise NotImplementedError
