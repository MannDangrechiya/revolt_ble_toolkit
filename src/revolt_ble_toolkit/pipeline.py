"""Runs the full HCI -> ATT -> GATT -> protocol classification pipeline over
a BTSnoop capture, and builds the summary counts shared by the CSV/JSON/
Markdown report exporter, the desktop GUI's Statistics pane, and the
cross-capture comparator.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from revolt_ble_toolkit.analyzers.gatt import GattAnalyzer, Service
from revolt_ble_toolkit.analyzers.protocol import ClassifiedPacket, ProtocolAnalyzer
from revolt_ble_toolkit.parsers.att import AttPacket, AttParser
from revolt_ble_toolkit.parsers.btsnoop import BtSnoopHciParser, HciPacket


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Everything the HCI -> ATT -> GATT -> protocol pipeline produced."""

    hci_packets: list[HciPacket]
    att_packets: list[AttPacket]
    services: list[Service]
    classified: list[ClassifiedPacket]


def run_pipeline(btsnoop_path: str | Path) -> PipelineResult:
    """Run the full pipeline over a BTSnoop capture file."""
    hci_packets = list(BtSnoopHciParser().parse_file(btsnoop_path))
    att_packets = list(AttParser().parse(hci_packets))
    services = GattAnalyzer().analyze(att_packets)
    classified = ProtocolAnalyzer().classify(att_packets, services)
    return PipelineResult(hci_packets, att_packets, services, classified)


def build_statistics(btsnoop_path: str | Path, result: PipelineResult) -> dict[str, Any]:
    """Packet/opcode/category counts, as used for statistics.json and the GUI's Statistics pane."""
    hci_packets, att_packets, services, classified = (
        result.hci_packets,
        result.att_packets,
        result.services,
        result.classified,
    )
    hci_by_type = Counter(p.packet_type.name for p in hci_packets)
    hci_by_direction = Counter(p.direction.value for p in hci_packets)
    connection_handles = sorted({p.acl.connection_handle for p in hci_packets if p.acl is not None})
    att_by_opcode = Counter(p.opcode.name for p in att_packets)
    category_groups: dict[str, list[float]] = {}
    for cp in classified:
        category_groups.setdefault(cp.category.value, []).append(cp.confidence)

    return {
        "source_file": str(btsnoop_path),
        "hci": {
            "total_packets": len(hci_packets),
            "by_type": dict(hci_by_type),
            "by_direction": dict(hci_by_direction),
            "connection_handles": connection_handles,
        },
        "att": {
            "total_packets": len(att_packets),
            "by_opcode": dict(att_by_opcode),
        },
        "gatt": {
            "services_discovered": len(services),
            "characteristics_discovered": sum(len(s.characteristics) for s in services),
            "descriptors_discovered": sum(
                len(c.descriptors) for s in services for c in s.characteristics
            ),
        },
        "protocol_classification": {
            category: {"count": len(scores), "avg_confidence": round(sum(scores) / len(scores), 2)}
            for category, scores in category_groups.items()
        },
    }
