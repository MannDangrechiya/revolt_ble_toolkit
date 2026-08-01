"""Base class for concrete record analyzers.

Concrete analyzers (added in a future milestone) subclass :class:`BaseAnalyzer`
and implement :meth:`analyze`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.core.models import AnalysisResult, ParsedRecord

logger = get_logger(__name__)


class BaseAnalyzer(ABC):
    """Common scaffolding shared by all analyzer implementations."""

    @abstractmethod
    def analyze(self, records: Iterable[ParsedRecord]) -> AnalysisResult:
        """Return an aggregated analysis result for the given records."""
        raise NotImplementedError
