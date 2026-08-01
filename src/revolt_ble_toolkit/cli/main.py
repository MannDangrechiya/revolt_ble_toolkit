"""Command-line entry point for the toolkit.

Subcommands:

- ``parse``   — parse just the HCI layer and print packet/connection counts.
- ``analyze`` — run the full pipeline (HCI -> ATT -> GATT -> classify) and
  print a summary, without writing any files.
- ``export``  — run the full pipeline and write commands.csv/notifications.csv/
  statistics.json/summary.md to ``--out-dir``.
- ``compare`` — diff two captures of the same device and print heuristically
  correlated changes (confidence-scored, never asserted as fact).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from revolt_ble_toolkit import __version__
from revolt_ble_toolkit.analyzers.compare import compare_captures, format_diff_report
from revolt_ble_toolkit.analyzers.protocol import generate_report
from revolt_ble_toolkit.config.logging_config import configure_logging, get_logger
from revolt_ble_toolkit.config.settings import get_settings
from revolt_ble_toolkit.core.exceptions import ToolkitError
from revolt_ble_toolkit.exporters.capture_report import build_statistics, generate_capture_report
from revolt_ble_toolkit.parsers.btsnoop import BtSnoopHciParser
from revolt_ble_toolkit.pipeline import run_pipeline

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="revolt-ble-toolkit",
        description=(
            "Professional toolkit for reverse engineering BLE traffic "
            "from Android HCI Snoop Logs."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    parse_cmd = subparsers.add_parser(
        "parse", help="Parse just the HCI layer and print packet/connection counts."
    )
    parse_cmd.add_argument("capture", type=Path, help="Path to a btsnoop_hci.log file")

    analyze_cmd = subparsers.add_parser(
        "analyze", help="Run the full pipeline and print a summary (no files written)."
    )
    analyze_cmd.add_argument("capture", type=Path, help="Path to a btsnoop_hci.log file")

    export_cmd = subparsers.add_parser(
        "export",
        help=(
            "Run the full pipeline and write commands.csv/notifications.csv/"
            "statistics.json/summary.md."
        ),
    )
    export_cmd.add_argument("capture", type=Path, help="Path to a btsnoop_hci.log file")
    export_cmd.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: the configured reports/ directory)",
    )

    compare_cmd = subparsers.add_parser(
        "compare", help="Diff two captures of the same device and correlate what changed."
    )
    compare_cmd.add_argument("capture1", type=Path, help="'Before' capture")
    compare_cmd.add_argument("capture2", type=Path, help="'After' capture")

    return parser


def _cmd_parse(args: argparse.Namespace) -> int:
    packets = list(BtSnoopHciParser().parse_file(args.capture))
    by_type: dict[str, int] = {}
    for packet in packets:
        by_type[packet.packet_type.name] = by_type.get(packet.packet_type.name, 0) + 1
    handles = sorted({p.acl.connection_handle for p in packets if p.acl is not None})

    print(f"{args.capture}: {len(packets)} HCI packets")
    for type_name, count in sorted(by_type.items()):
        print(f"  {type_name}: {count}")
    print(f"  connection handles: {handles}")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    result = run_pipeline(args.capture)
    print(json.dumps(build_statistics(args.capture, result), indent=2))
    print()
    print(generate_report(result.classified), end="")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    out_dir = args.out_dir or get_settings().paths.reports_dir
    paths = generate_capture_report(args.capture, out_dir)
    print(f"Wrote {paths.commands_csv}")
    print(f"Wrote {paths.notifications_csv}")
    print(f"Wrote {paths.statistics_json}")
    print(f"Wrote {paths.summary_md}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    diffs = compare_captures(args.capture1, args.capture2)
    print(format_diff_report(diffs), end="")
    return 0


_COMMANDS = {
    "parse": _cmd_parse,
    "analyze": _cmd_analyze,
    "export": _cmd_export,
    "compare": _cmd_compare,
}


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point used by ``python -m revolt_ble_toolkit`` and the console script."""
    settings = get_settings()
    configure_logging(settings)

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        return _COMMANDS[args.command](args)
    except (ToolkitError, OSError) as exc:
        logger.error("%s command failed: %s", args.command, exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
