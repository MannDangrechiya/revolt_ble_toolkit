"""CLI for the live BLE client.

Usage: ``revolt-ble-live [--address MAC] [--name RV400] [--pair TOKEN] [--save PATH]``
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from revolt_ble_toolkit.core.exceptions import LiveClientError
from revolt_ble_toolkit.live.client import RevoltLiveClient


async def _run(args: argparse.Namespace) -> int:
    client = RevoltLiveClient(name_filter=args.name, save_path=args.save)
    try:
        await client.connect(args.address)
    except LiveClientError as exc:
        print(f"Connection failed: {exc}")
        return 1

    if args.pair:
        accepted = await client.pair(args.pair)
        print("PAIR handshake:", "ACCEPTED" if accepted else "no ACCEPTED response (timed out)")

    print("Connected. Listening for notifications — Ctrl+C to stop.")
    try:
        while client.is_connected:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await client.disconnect()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="revolt-ble-live", description="Live BLE client for the Revolt RV400."
    )
    parser.add_argument(
        "--address", help="Known BLE MAC/UUID to connect to directly (skips scanning)"
    )
    parser.add_argument(
        "--name", default="RV400", help="Advertised-name substring to scan for (default: RV400)"
    )
    parser.add_argument(
        "--pair", metavar="TOKEN", help="Run the PAIR handshake with this token after connecting"
    )
    parser.add_argument(
        "--save", type=Path, help="Append every notification/write as JSON lines to this file"
    )
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
