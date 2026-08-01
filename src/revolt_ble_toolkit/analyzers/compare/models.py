"""Object model for cross-capture byte-diff + automatic correlation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CorrelationCategory(Enum):
    """Physical quantity a changed handle's value is heuristically guessed to represent."""

    BATTERY = "battery"
    VOLTAGE = "voltage"
    TEMPERATURE = "temperature"
    GPS = "gps"
    RIDE_MODE = "ride_mode"
    CHARGING = "charging"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HandleDiff:
    """A GATT attribute handle whose notified value differs between two captures."""

    attribute_handle: int
    uuid: str | None
    capture1_last_value: bytes | None  # None if the handle never notified in capture 1
    capture2_last_value: bytes | None  # None if the handle never notified in capture 2
    category: CorrelationCategory
    confidence: float
    reason: str

    @property
    def changed_byte_offsets(self) -> tuple[int, ...]:
        """Byte indices that differ, when both values are present and the same length."""
        a, b = self.capture1_last_value, self.capture2_last_value
        if a is None or b is None or len(a) != len(b):
            return ()
        return tuple(i for i, (x, y) in enumerate(zip(a, b, strict=True)) if x != y)
