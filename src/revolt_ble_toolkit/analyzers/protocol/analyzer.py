"""Classifies ATT traffic into protocol roles using simple heuristics.

Classification happens per "channel" — the (connection_handle,
attribute_handle) a Read/Write/Notify/Indicate targets — not per packet,
because heuristics like "fires at a regular interval" or "many same-sized
writes in a row" only make sense across a channel's history. Every packet
on a channel gets that channel's classification.

Read Response carries no handle of its own (ATT is lockstep request/response
per connection), so it's attributed to the handle of the most recent Read
Request on that connection. Exchange MTU and GATT-discovery responses have
no attribute handle at all and are classified directly as Configuration.

Heuristics are a plain priority-ordered decision list (first match wins),
not a weighted scorer — easier to read, easier to debug a wrong call.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from revolt_ble_toolkit.analyzers.gatt import Service
from revolt_ble_toolkit.analyzers.protocol.models import ClassifiedPacket, PacketCategory
from revolt_ble_toolkit.parsers.att import AttOpcode, AttPacket

# A handful of well-known 16-bit Bluetooth SIG UUIDs — enough to recognize
# common device roles. Not exhaustive: custom/vendor UUIDs fall through to
# the behavioral heuristics below.
_FIRMWARE_UUIDS = {"2a26", "2a28"}  # Firmware Revision String, Software Revision String
_TELEMETRY_UUIDS = {"2a19", "2a37", "2a38", "2a1c", "2a6e", "2a6d", "2a6f"}
_CONFIG_UUIDS = {"2a00", "2a01", "2902", "2903", "2901"}

_NOTIFY_LIKE = {AttOpcode.HANDLE_VALUE_NOTIFICATION, AttOpcode.HANDLE_VALUE_INDICATION}
_WRITE_LIKE = {AttOpcode.WRITE_REQUEST, AttOpcode.WRITE_COMMAND}
_NO_HANDLE_CONFIG_OPCODES = {
    AttOpcode.EXCHANGE_MTU_REQUEST,
    AttOpcode.EXCHANGE_MTU_RESPONSE,
    AttOpcode.READ_BY_GROUP_TYPE_RESPONSE,
    AttOpcode.READ_BY_TYPE_RESPONSE,
    AttOpcode.FIND_INFORMATION_RESPONSE,
}


def _shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    length = len(data)
    return -sum((n / length) * math.log2(n / length) for n in Counter(data).values())


@dataclass
class _Channel:
    uuid: str | None = None
    opcodes: list[AttOpcode] = field(default_factory=list)
    sizes: list[int] = field(default_factory=list)
    values: list[bytes] = field(default_factory=list)
    timestamps: list[float] = field(default_factory=list)


class ProtocolAnalyzer:
    """Classifies ATT traffic by (connection_handle, attribute_handle) channel."""

    def classify(
        self, att_packets: Iterable[AttPacket], services: Iterable[Service] = ()
    ) -> list[ClassifiedPacket]:
        packets = list(att_packets)
        handle_uuids = self._handle_uuids(services)

        channels: dict[tuple[int, int], _Channel] = defaultdict(_Channel)
        channel_key_of: list[tuple[int, int] | None] = []
        last_read_request: dict[int, int] = {}

        for att in packets:
            if att.opcode is AttOpcode.READ_REQUEST and att.attribute_handle is not None:
                last_read_request[att.connection_handle] = att.attribute_handle

            handle = att.attribute_handle
            if handle is None and att.opcode is AttOpcode.READ_RESPONSE:
                handle = last_read_request.get(att.connection_handle)

            if handle is None:
                channel_key_of.append(None)
                continue

            key = (att.connection_handle, handle)
            channel_key_of.append(key)
            channel = channels[key]
            channel.uuid = channel.uuid or handle_uuids.get(handle)
            channel.opcodes.append(att.opcode)
            channel.sizes.append(len(att.value))
            channel.values.append(att.value)
            channel.timestamps.append(att.timestamp.timestamp())

        classification_of: dict[tuple[int, int], tuple[PacketCategory, float, str]] = {
            key: self._classify_channel(channel) for key, channel in channels.items()
        }

        results = []
        for att, channel_key in zip(packets, channel_key_of, strict=True):
            category, confidence, reason = (
                self._classify_no_handle(att)
                if channel_key is None
                else classification_of[channel_key]
            )
            results.append(ClassifiedPacket(att, category, confidence, reason))
        return results

    @staticmethod
    def _handle_uuids(services: Iterable[Service]) -> dict[int, str]:
        mapping: dict[int, str] = {}
        for service in services:
            for char in service.characteristics:
                mapping[char.declaration_handle] = char.uuid
                mapping[char.value_handle] = char.uuid
                for descriptor in char.descriptors:
                    mapping[descriptor.handle] = descriptor.uuid
        return mapping

    @staticmethod
    def _classify_no_handle(att: AttPacket) -> tuple[PacketCategory, float, str]:
        if att.opcode in (AttOpcode.EXCHANGE_MTU_REQUEST, AttOpcode.EXCHANGE_MTU_RESPONSE):
            return PacketCategory.CONFIGURATION, 0.8, "MTU negotiation"
        if att.opcode in _NO_HANDLE_CONFIG_OPCODES:
            return PacketCategory.CONFIGURATION, 0.6, "GATT discovery response"
        return PacketCategory.UNKNOWN, 0.0, "no attribute handle and no known signal"

    @staticmethod
    def _classify_channel(channel: _Channel) -> tuple[PacketCategory, float, str]:
        uuid = channel.uuid
        if uuid in _FIRMWARE_UUIDS:
            return PacketCategory.FIRMWARE, 0.9, f"known firmware-related UUID {uuid}"
        if uuid in _TELEMETRY_UUIDS:
            return PacketCategory.TELEMETRY, 0.9, f"known telemetry UUID {uuid}"
        if uuid in _CONFIG_UUIDS:
            return PacketCategory.CONFIGURATION, 0.85, f"known configuration UUID {uuid}"

        opcodes = channel.opcodes
        mean_size = statistics.fmean(channel.sizes) if channel.sizes else 0.0

        write_commands = sum(1 for op in opcodes if op is AttOpcode.WRITE_COMMAND)
        if write_commands >= 4 and mean_size >= 16:
            return (
                PacketCategory.FIRMWARE,
                0.7,
                f"{write_commands} write-without-response packets averaging {mean_size:.0f} bytes",
            )

        if (
            AttOpcode.WRITE_REQUEST in opcodes
            and any(size in (16, 20, 32) for size in channel.sizes)
            and any(_shannon_entropy(v) >= 3.5 for v in channel.values)
        ):
            return (
                PacketCategory.AUTHENTICATION,
                0.6,
                "write-request with key-sized, high-entropy payload",
            )

        if len(opcodes) >= 3 and any(op in _NOTIFY_LIKE for op in opcodes):
            intervals = [
                b - a for a, b in zip(channel.timestamps, channel.timestamps[1:], strict=False)
            ]
            mean_interval = statistics.fmean(intervals) if intervals else 0.0
            if mean_interval > 0:
                cv = statistics.pstdev(intervals) / mean_interval
                constant_value = len(set(channel.values)) == 1
                if (cv < 0.3 or constant_value) and mean_size <= 4:
                    return (
                        PacketCategory.HEARTBEAT,
                        0.65,
                        f"regular small notifications (interval cv={cv:.2f})",
                    )

        if (
            any(op in _NOTIFY_LIKE or op is AttOpcode.READ_RESPONSE for op in opcodes)
            and len(set(channel.values)) > 1
        ):
            return PacketCategory.TELEMETRY, 0.5, "changing notified/read values"

        if any(op in _WRITE_LIKE for op in opcodes):
            return PacketCategory.CONFIGURATION, 0.4, "generic write, no stronger signal"

        return PacketCategory.UNKNOWN, 0.0, "no heuristic matched"


def generate_report(classified: Sequence[ClassifiedPacket]) -> str:
    """Render a plain-text summary: per-category packet counts and average confidence."""
    if not classified:
        return "No packets classified.\n"

    by_category: dict[PacketCategory, list[ClassifiedPacket]] = defaultdict(list)
    for cp in classified:
        by_category[cp.category].append(cp)

    lines = [f"Protocol Analysis Report ({len(classified)} packets)", "=" * 40]
    for category in PacketCategory:
        group = by_category.get(category, [])
        if not group:
            continue
        avg_confidence = statistics.fmean(cp.confidence for cp in group)
        lines.append(
            f"{category.value:<15} {len(group):>5} packets  avg confidence {avg_confidence:.2f}"
        )
    return "\n".join(lines) + "\n"
