"""Command-line entry point for the toolkit.

Only wiring lives here: argument parsing and dispatch. No parsing/analysis
logic is implemented yet - subcommands currently report that they are
pending a future milestone.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from revolt_ble_toolkit import __version__
from revolt_ble_toolkit.config.logging_config import configure_logging, get_logger
from revolt_ble_toolkit.config.settings import get_settings

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
    subparsers.add_parser("parse", help="Parse a capture log into records (not yet implemented).")
    subparsers.add_parser("analyze", help="Analyze parsed records (not yet implemented).")
    subparsers.add_parser("export", help="Export analysis results (not yet implemented).")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point used by ``python -m revolt_ble_toolkit`` and the console script."""
    settings = get_settings()
    configure_logging(settings)

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    logger.info("Command '%s' requested; business logic not yet implemented.", args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
