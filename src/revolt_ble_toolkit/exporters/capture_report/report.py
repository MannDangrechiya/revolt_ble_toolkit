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
from dataclasses import dataclass
from pathlib import Path

from revolt_ble_toolkit.analyzers.gatt import Service, handle_uuid_map
from revolt_ble_toolkit.analyzers.protocol import ClassifiedPacket, generate_report
from revolt_ble_toolkit.core.exceptions import ExportError
from revolt_ble_toolkit.parsers.att import AttOpcode, AttPacket
from revolt_ble_toolkit.parsers.btsnoop import HciPacket
from revolt_ble_toolkit.pipeline import PipelineResult, build_statistics, run_pipeline

__all__ = [
    "CaptureReportPaths",
    "PipelineResult",
    "build_statistics",
    "generate_capture_report",
    "run_pipeline",
]

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


def generate_capture_report(btsnoop_path: str | Path, out_dir: str | Path) -> CaptureReportPaths:
    """Parse ``btsnoop_path`` and write the four report files into ``out_dir``.

    :raises ExportError: If ``out_dir`` can't be created or any report file
        can't be written (e.g. permission denied, disk full).
    """
    out_dir = Path(out_dir)
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

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_att_csv(paths.commands_csv, att_packets, AttOpcode.WRITE_COMMAND, handle_uuids)
        _write_att_csv(
            paths.notifications_csv,
            att_packets,
            AttOpcode.HANDLE_VALUE_NOTIFICATION,
            handle_uuids,
        )
        paths.statistics_json.write_text(
            json.dumps(build_statistics(btsnoop_path, result), indent=2) + "\n", encoding="utf-8"
        )
        _write_summary_md(
            paths.summary_md, btsnoop_path, hci_packets, att_packets, services, classified
        )
    except OSError as exc:
        raise ExportError(f"Failed to write report to {out_dir}: {exc}") from exc

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
