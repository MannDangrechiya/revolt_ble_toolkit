"""Base class for concrete capture-log parsers.

Concrete parsers (added in a future milestone) subclass :class:`BaseLogParser`
and implement :meth:`supports` and :meth:`parse`. New formats can be added
without modifying existing parsers or their callers (Open/Closed Principle).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.core.models import CaptureFile, ParsedRecord

logger = get_logger(__name__)


class BaseLogParser(ABC):
    """Common scaffolding shared by all log parser implementations."""

    @abstractmethod
    def supports(self, capture: CaptureFile) -> bool:
        """Return True if this parser can handle the given capture file."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, capture: CaptureFile) -> Iterator[ParsedRecord]:
        """Yield parsed records from the capture file."""
        raise NotImplementedError
