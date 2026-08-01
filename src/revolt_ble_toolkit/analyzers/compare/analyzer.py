"""Compares two BTSnoop captures of the same device and heuristically
correlates whichever GATT attribute handles changed to a guessed physical
quantity (battery / voltage / temperature / GPS / ride mode / charging).

Only Notification/Indication values are compared: telemetry a peripheral
pushes on its own is what changes between a "before" and "after" capture.
Read Request/Response round-trips are a separate correlation problem (that
logic already exists in ProtocolAnalyzer) and aren't needed for this
workflow — see the ponytail note below if a real capture needs it.

Attribute handles, not connection handles, are the comparison key: GATT
handles are assigned from the peripheral's fixed attribute table and stay
stable across separate connections to the same device, whereas connection
handles are assigned per-session by the controller and mean nothing across
two independently captured files.

Every non-UUID-backed correlation is a byte-pattern guess with a modest
confidence score and a plain-English reason — never treat it as fact. Some
ranges are inherently ambiguous by bytes alone (e.g. a 2-byte value of 3700
could be 3.700V or a coincidentally similar quantity) — only the numeric
windows below are checked, not an attempt to resolve every ambiguity.
"""

from __future__ import annotations

import struct
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from revolt_ble_toolkit.analyzers.compare.models import CorrelationCategory, HandleDiff
from revolt_ble_toolkit.analyzers.gatt import handle_uuid_map
from revolt_ble_toolkit.parsers.att import AttOpcode

if TYPE_CHECKING:
    # Deferred: revolt_ble_toolkit.pipeline imports analyzers.gatt/protocol,
    # which would cycle back here if imported at module load time (it's
    # only needed for the type hints below and the lazy import in
    # compare_captures()).
    from revolt_ble_toolkit.pipeline import PipelineResult

_BATTERY_UUIDS = {"2a19"}
_TEMPERATURE_UUIDS = {"2a1c", "2a6e"}
_NOTIFY_LIKE = {AttOpcode.HANDLE_VALUE_NOTIFICATION, AttOpcode.HANDLE_VALUE_INDICATION}


class CaptureComparator:
    """Diffs two captures' notified values by attribute handle and correlates changes."""

    def compare(self, capture1: PipelineResult, capture2: PipelineResult) -> list[HandleDiff]:
        values1 = self._notified_values_by_handle(capture1)
        values2 = self._notified_values_by_handle(capture2)
        handle_uuids = {
            **handle_uuid_map(capture1.services),
            **handle_uuid_map(capture2.services),
        }

        diffs = []
        for handle in sorted(set(values1) | set(values2)):
            last1 = values1[handle][-1] if handle in values1 else None
            last2 = values2[handle][-1] if handle in values2 else None
            if last1 == last2:
                continue  # unchanged between captures — not interesting for this workflow

            uuid = handle_uuids.get(handle)
            all_values = values1.get(handle, []) + values2.get(handle, [])
            category, confidence, reason = self._correlate(uuid, all_values)
            diffs.append(HandleDiff(handle, uuid, last1, last2, category, confidence, reason))
        return diffs

    @staticmethod
    def _notified_values_by_handle(result: PipelineResult) -> dict[int, list[bytes]]:
        # ponytail: Notify/Indicate only, no Read Response correlation. Add
        # it (reusing ProtocolAnalyzer's read-request/response pairing) if a
        # real capture shows the telemetry only arrives via reads.
        values: dict[int, list[bytes]] = defaultdict(list)
        for att in result.att_packets:
            if att.opcode in _NOTIFY_LIKE and att.attribute_handle is not None:
                values[att.attribute_handle].append(att.value)
        return values

    @staticmethod
    def _correlate(uuid: str | None, values: list[bytes]) -> tuple[CorrelationCategory, float, str]:
        if uuid in _BATTERY_UUIDS:
            return CorrelationCategory.BATTERY, 0.95, f"known Battery Level UUID {uuid}"
        if uuid in _TEMPERATURE_UUIDS:
            return CorrelationCategory.TEMPERATURE, 0.95, f"known Temperature UUID {uuid}"

        distinct = {v for v in values if v is not None}
        if not distinct:
            return CorrelationCategory.UNKNOWN, 0.0, "no observed values"

        if all(len(v) == 1 for v in distinct):
            byte_values = {v[0] for v in distinct}
            if byte_values <= {0, 1}:
                return CorrelationCategory.CHARGING, 0.55, "single boolean-like byte (0/1)"
            if len(byte_values) <= 5 and max(byte_values) <= 10:
                return (
                    CorrelationCategory.RIDE_MODE,
                    0.45,
                    f"single byte with {len(byte_values)} small discrete values (enum-like)",
                )
            if max(byte_values) <= 100:
                return (
                    CorrelationCategory.BATTERY,
                    0.5,
                    "single byte in 0-100 range (percentage-like)",
                )

        elif all(len(v) == 2 for v in distinct):
            signed = [struct.unpack("<h", v)[0] for v in distinct]
            if all(-20 <= t <= 80 for t in signed):
                return (
                    CorrelationCategory.TEMPERATURE,
                    0.4,
                    "2-byte signed value in plausible Celsius range",
                )
            unsigned = [struct.unpack("<H", v)[0] for v in distinct]
            if all(2500 <= mv <= 5000 for mv in unsigned):
                return (
                    CorrelationCategory.VOLTAGE,
                    0.35,
                    "2-byte unsigned value in plausible millivolt range (2.5-5.0V)",
                )
            if all(250 <= cv <= 500 for cv in unsigned):
                return (
                    CorrelationCategory.VOLTAGE,
                    0.3,
                    "2-byte unsigned value in plausible centivolt range (2.50-5.00V)",
                )

        elif all(len(v) == 4 for v in distinct):
            floats = [struct.unpack("<f", v)[0] for v in distinct]
            if all(-180.0 <= f <= 180.0 for f in floats) and any(abs(f) > 0.001 for f in floats):
                return (
                    CorrelationCategory.GPS,
                    0.3,
                    "4-byte little-endian float in plausible latitude/longitude range",
                )

        return CorrelationCategory.UNKNOWN, 0.0, "no heuristic matched"


def compare_captures(capture1_path: str | Path, capture2_path: str | Path) -> list[HandleDiff]:
    """Parse two BTSnoop files and return the changed-handle correlations between them."""
    from revolt_ble_toolkit.pipeline import run_pipeline

    return CaptureComparator().compare(run_pipeline(capture1_path), run_pipeline(capture2_path))


def format_diff_report(diffs: list[HandleDiff]) -> str:
    """Render a plain-text summary of :func:`compare_captures`'s output, for the CLI/GUI alike."""
    if not diffs:
        return "No changed handles detected between the two captures.\n"

    lines = []
    for diff in diffs:
        value1, value2 = diff.capture1_last_value, diff.capture2_last_value
        before = value1.hex() if value1 is not None else "(absent)"
        after = value2.hex() if value2 is not None else "(absent)"
        lines.append(
            f"handle {diff.attribute_handle} (uuid={diff.uuid or 'unknown'}): "
            f"{diff.category.value} (confidence {diff.confidence:.2f}) — {diff.reason}"
        )
        lines.append(f"  before: {before}")
        lines.append(f"  after:  {after}")
    return "\n".join(lines) + "\n"
