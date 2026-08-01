"""Runs the full pipeline (HCI -> ATT -> GATT -> protocol classification) over
a BTSnoop capture and writes four output files: commands.csv, notifications.csv,
statistics.json, summary.md.

Only what the parsers/analyzers actually decoded is reported. Attribute
handles with no UUID discovered in this capture are left blank rather than
guessed, and heuristic protocol categories are always shown with their
confidence score, never stated as fact.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from revolt_ble_toolkit.analyzers.gatt import GattAnalyzer, Service, handle_uuid_map
from revolt_ble_toolkit.analyzers.protocol import (
    ClassifiedPacket,
    ProtocolAnalyzer,
    generate_report,
)
from revolt_ble_toolkit.parsers.att import AttOpcode, AttPacket, AttParser
from revolt_ble_toolkit.parsers.btsnoop import BtSnoopHciParser, HciPacket

_CSV_FIELDS = [
    "hci_number",
    "timestamp",
    "connection_handle",
    "attribute_handle",
    "uuid",
    "value_hex",
    "value_length",
]


@dataclass(frozen=True, slots=True)
class CaptureReportPaths:
    """Paths to the four files written by :func:`generate_capture_report`."""

    commands_csv: Path
    notifications_csv: Path
    statistics_json: Path
    summary_md: Path


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
    """Build the same counts dict used for statistics.json, for reuse elsewhere (e.g. a GUI)."""
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


def generate_capture_report(btsnoop_path: str | Path, out_dir: str | Path) -> CaptureReportPaths:
    """Parse ``btsnoop_path`` and write the four report files into ``out_dir``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    btsnoop_path = Path(btsnoop_path)

    result = run_pipeline(btsnoop_path)
    hci_packets, att_packets, services, classified = (
        result.hci_packets,
        result.att_packets,
        result.services,
        result.classified,
    )
    handle_uuids = handle_uuid_map(services)

    paths = CaptureReportPaths(
        commands_csv=out_dir / "commands.csv",
        notifications_csv=out_dir / "notifications.csv",
        statistics_json=out_dir / "statistics.json",
        summary_md=out_dir / "summary.md",
    )

    _write_att_csv(paths.commands_csv, att_packets, AttOpcode.WRITE_COMMAND, handle_uuids)
    _write_att_csv(
        paths.notifications_csv, att_packets, AttOpcode.HANDLE_VALUE_NOTIFICATION, handle_uuids
    )
    paths.statistics_json.write_text(
        json.dumps(build_statistics(btsnoop_path, result), indent=2) + "\n", encoding="utf-8"
    )
    _write_summary_md(
        paths.summary_md, btsnoop_path, hci_packets, att_packets, services, classified
    )

    return paths


def _write_att_csv(
    path: Path, att_packets: list[AttPacket], opcode: AttOpcode, handle_uuids: dict[int, str]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(_CSV_FIELDS)
        for att in att_packets:
            if att.opcode is not opcode:
                continue
            handle = att.attribute_handle
            writer.writerow(
                [
                    att.hci_number,
                    att.timestamp.isoformat(),
                    att.connection_handle,
                    handle if handle is not None else "",
                    handle_uuids.get(handle, "") if handle is not None else "",
                    att.value.hex(),
                    len(att.value),
                ]
            )


def _write_summary_md(
    path: Path,
    btsnoop_path: Path,
    hci_packets: list[HciPacket],
    att_packets: list[AttPacket],
    services: list[Service],
    classified: list[ClassifiedPacket],
) -> None:
    connection_handles = sorted({p.acl.connection_handle for p in hci_packets if p.acl is not None})
    lines = [
        "# Capture Summary",
        "",
        f"Source: `{btsnoop_path}`",
        "",
        "## Overview",
        "",
        f"- HCI packets: {len(hci_packets)}",
        f"- ATT packets decoded: {len(att_packets)}",
        f"- Connection handles seen: {connection_handles}",
    ]
    if hci_packets:
        lines.append(
            f"- Time range: {hci_packets[0].timestamp.isoformat()} to "
            f"{hci_packets[-1].timestamp.isoformat()}"
        )

    lines += ["", "## GATT Discovery", ""]
    if not services:
        lines.append(
            "No GATT discovery PDUs (Read By Group Type / Read By Type / "
            "Find Information responses) were found in this capture."
        )
    else:
        lines.append("| Service UUID | Handles | Characteristics |")
        lines.append("|---|---|---|")
        for s in sorted(services, key=lambda svc: svc.start_handle):
            lines.append(
                f"| `{s.uuid}` | {s.start_handle}-{s.end_handle} | {len(s.characteristics)} |"
            )

    lines += [
        "",
        "## Protocol Classification (heuristic — confidence scores, not ground truth)",
        "",
        "```",
        generate_report(classified).rstrip("\n"),
        "```",
        "",
        "## Output Files",
        "",
        "- `commands.csv` — ATT Write Command packets",
        "- `notifications.csv` — ATT Handle Value Notification packets",
        "- `statistics.json` — packet/opcode/category counts",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
