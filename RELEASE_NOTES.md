# Release Notes — v1.0.0

## What this is

A complete, production-ready toolkit for reverse-engineering BLE traffic from Android HCI Snoop Logs — built against, and validated with, a real device (a Revolt RV400 e-bike) rather than assumed protocol behavior.

## What you get

- **Offline analysis**, from a `btsnoop_hci.log` file to a full picture: HCI framing → ATT PDUs → GATT services/characteristics/descriptors → heuristic protocol-role classification, all as one function call (`pipeline.run_pipeline`) or one CLI command (`revolt-ble-toolkit analyze`).
- **A CLI** (`revolt-ble-toolkit parse|analyze|export|compare`) that's actually implemented — every subcommand does real work, none are placeholders.
- **A desktop GUI** (`revolt-ble-gui`) — drag a capture in, get a searchable/filterable packet table, a click-to-seek timeline, hex/ASCII/statistics panes, dark theme, plus a `File` menu for exporting a report, comparing with a second capture, a persisted recent-captures list, and keyboard shortcuts.
- **Cross-capture comparison** (`revolt-ble-toolkit compare`) — capture the same device in two states and see exactly which GATT handles changed, with a heuristic (confidence-scored) guess at what each change might represent.
- **A live BLE client** (`revolt-ble-live`, Bleak-based) — connect to a real device, not just a capture file: scan, connect, discover, subscribe, run the PAIR handshake, auto-reconnect, and expose every raw notification and write.
- **A Flutter SDK** (`flutter_sdk/`) — the same live-client capability for a mobile app, plus a runnable demo.

## The one thing that makes this different from a typical reverse-engineering script

Every piece of decoded information is labeled by how certain it actually is. Wire-format facts (byte order, opcodes, PDU shapes) are Bluetooth-spec-confirmed. Device-specific facts (which characteristic carries which traffic) are labeled as directly observed from a real capture, with a note on how many times and how it was re-verified. Anything else — is this byte battery or temperature, did this handle's change mean charging started — is a heuristic guess with a numeric confidence score and a one-line reason, never presented as settled fact. See `KNOWN_LIMITATIONS.md` for the full confirmed/likely/unknown breakdown.

## Quality bar for this release

- 142 tests, all passing.
- 92% line coverage — the remaining 8% is thin UI/CLI entry-point wiring and a handful of documented, deliberately-untestable-without-hardware paths, not untested logic.
- Zero Ruff findings, zero Black reformats, zero MyPy errors (`--strict`) across the whole `src/`+`tests/` tree.
- Zero known import cycles, zero dead code, zero unused modules — verified by direct usage search, not assumed.
- A real crash bug (malformed GATT discovery data could raise an unhandled `struct.error`) was found and fixed as part of getting to this release, not left for later.

## Upgrading from pre-1.0

There is no prior tagged release — this is the first. If you have code depending on `core.interfaces`, `parsers.base`/`analyzers.base`/`exporters.base`, `core.models`, `core.enums`, or `utils.paths`: those were unused scaffolding, confirmed via direct search before removal, and are gone in this release. Nothing that had a real caller was removed. See `CHANGELOG.md`.

## Install

```bash
uv sync --all-extras
# or
pip install -e ".[gui,live]"
```

See `README.md` for the full quickstart, `DEVELOPER_GUIDE.md` if you're contributing.
