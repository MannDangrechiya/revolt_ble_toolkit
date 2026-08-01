# Revolt BLE Toolkit

[![CI](https://github.com/MannDangrechiya/revolt_ble_toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/MannDangrechiya/revolt_ble_toolkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

A professional toolkit for reverse engineering Bluetooth Low Energy (BLE) traffic
captured in **Android HCI Snoop Logs**.

> **Status: v1.0.0.** All modules complete: HCI/ATT parsing, GATT discovery,
> heuristic protocol classification, cross-capture comparison, a desktop GUI,
> a live BLE client, and a Flutter mobile SDK — all backed by a fully-wired
> CLI. See [PROJECT_AUDIT.md](PROJECT_AUDIT.md) for the full v1.0
> production-readiness audit, [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)
> for what's confirmed vs. heuristic vs. still unknown about the protocol,
> and [ROADMAP.md](ROADMAP.md) for what's next.

## Requirements

- Python **3.12**
- [uv](https://docs.astral.sh/uv/) (preferred) or `pip`
- The desktop GUI needs the optional `gui` extra (PySide6) — see below.
- The live BLE client needs the optional `live` extra (Bleak) and a real
  Bluetooth adapter — see below.

## Project layout

```text
revolt_ble_toolkit/
├── .github/workflows/         # CI (lint/type/test) and tag-triggered release builds
├── LICENSE                    # MIT
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── SECRETS_POLICY.md          # Gitleaks: CI + local pre-commit secret scanning
├── .gitleaks.toml             # allowlist for the known, already-tracked incident docs
├── pyproject.toml            # Project metadata, dependencies, tool config (Ruff/Black/MyPy/pytest)
├── requirements.txt          # Runtime deps (pip fallback)
├── requirements-dev.txt      # Dev/tooling deps (pip fallback)
├── config/
│   └── default.toml          # Default application configuration
├── logs/                     # Rotating log files are written here at runtime
├── src/
│   └── revolt_ble_toolkit/
│       ├── __init__.py
│       ├── __main__.py       # `python -m revolt_ble_toolkit`
│       ├── pipeline.py         # Orchestrates parse -> ATT -> GATT -> classify
│       ├── cli/                # `revolt-ble-toolkit`: parse/analyze/export/compare
│       │   └── main.py
│       ├── config/            # Layered settings (dataclasses) + logging setup
│       │   ├── settings.py
│       │   └── logging_config.py
│       ├── core/               # Toolkit-wide exception hierarchy only
│       │   └── exceptions.py
│       ├── parsers/            # Capture-log parsers
│       │   ├── btsnoop/        # Module 1: BTSnoop HCI parser
│       │   └── att/            # Module 2: ATT PDU parser
│       ├── analyzers/
│       │   ├── gatt/           # Module 3: GATT hierarchy analyzer
│       │   ├── protocol/       # Module 4: heuristic protocol classifier
│       │   └── compare/        # Module 6: cross-capture comparator
│       ├── exporters/
│       │   └── capture_report/ # commands.csv/notifications.csv/statistics.json/summary.md
│       ├── gui/                 # PySide6 desktop GUI
│       │   ├── app.py           # Entry point + dark theme (`revolt-ble-gui`)
│       │   ├── main_window.py   # Drag-and-drop, filters/search, hex/ASCII/stats panes
│       │   └── widgets.py       # Table model, filter proxy, timeline widget
│       └── live/                # Live BLE client (Bleak) (`revolt-ble-live`)
│           ├── client.py
│           ├── cli.py
│           └── models.py
├── docs/
│   ├── hci_parser.md         # Module 1 documentation
│   └── att_parser.md         # Module 2 documentation
├── ARCHITECTURE.md           # why the codebase is shaped this way
├── PIPELINE.md               # the end-to-end data flow
├── DEVELOPER_GUIDE.md        # setup, conventions, how to add a module
├── MODULE_REFERENCE.md       # what each module does
├── API_REFERENCE.md          # the public symbol list
├── PROJECT_AUDIT.md          # v1.0 production-readiness audit
├── FINAL_STATUS.md           # condensed completion/readiness summary
├── RELEASE_NOTES.md          # v1.0.0 release announcement
├── REMAINING_TASKS.md        # the concrete, categorized backlog
├── KNOWN_LIMITATIONS.md      # confirmed vs. heuristic vs. unknown protocol facts
├── ROADMAP.md                # forward-looking direction
├── CHANGELOG.md
├── HISTORY_SANITIZATION.md   # git-history PII incident: full remediation procedure
├── SECURITY_RELEASE_CHECKLIST.md  # pre-public-release security checklist
├── RELEASE_CHECKLIST.md      # open-source packaging/release-infra checklist
├── CLEANUP_REPORT.md         # non-production-artifact removal log
├── VERSION
└── tests/
    ├── test_cli/
    ├── test_config/
    ├── test_core/
    ├── test_parsers/
    ├── test_analyzers/
    ├── test_exporters/
    ├── test_gui/
    └── test_live/
```

## Architecture

Every module owns its own strongly-typed dataclasses (`HciPacket`, `AttPacket`,
`Service`/`Characteristic`, `ClassifiedPacket`, `HandleDiff`, ...) rather than
conforming to a shared generic envelope — an earlier generic
interface/base-class layer was tried in the foundation and never adopted by
any of the six parser/analyzer/exporter modules built since, so it was
removed rather than kept as unused abstraction (see
[ARCHITECTURE.md](ARCHITECTURE.md) for the full reasoning). `core` is just
the shared exception hierarchy now (`ToolkitError` and its subclasses).

`pipeline.py` is the one place that wires the modules together end to end
(HCI parse → ATT decode → GATT discovery → protocol classification); the CLI,
GUI, capture-report exporter, and comparator all call into it rather than
each re-implementing the sequence. See [PIPELINE.md](PIPELINE.md) for the
full data flow and [MODULE_REFERENCE.md](MODULE_REFERENCE.md) /
[API_REFERENCE.md](API_REFERENCE.md) for per-module detail.

## Configuration system

Settings are modeled as frozen dataclasses in
[`config/settings.py`](src/revolt_ble_toolkit/config/settings.py):

- `AppSettings` — root settings (`environment`, `debug`, nested `paths`, `logging`)
- `PathSettings` — filesystem locations (data, logs, reports)
- `LoggingSettings` — log level, format, rotation

Values are resolved in layers, each one overriding the last:

1. Dataclass defaults
2. [`config/default.toml`](config/default.toml)
3. Environment variables prefixed with `REVOLT_` (e.g. `REVOLT_DEBUG=true`,
   `REVOLT_LOGGING_LEVEL=DEBUG`)

Call `get_settings()` to obtain the cached singleton; never read files or
environment variables directly from other modules.

## Logging

`revolt_ble_toolkit.config.logging_config` configures a single package-root
logger with a console handler and an optional rotating file handler (written
to `logs/`). Modules obtain a logger via:

```python
from revolt_ble_toolkit.config.logging_config import get_logger

logger = get_logger(__name__)
```

## Getting started

### With uv (preferred)

```bash
uv sync --all-extras
uv run pytest
uv run revolt-ble-toolkit --help
uv run revolt-ble-gui                      # desktop GUI
uv run revolt-ble-gui btsnoop_hci.log      # ...opened directly on a capture
uv run revolt-ble-live --pair TOKEN123     # live client: scan, connect, pair
```

### With pip

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e ".[gui,live]"    # GUI (PySide6) + live client (Bleak); omit either for headless/library use
pytest
revolt-ble-toolkit --help
revolt-ble-gui
revolt-ble-live --help
```

## Development tooling

| Tool      | Purpose               | Command                    |
|-----------|-----------------------|-----------------------------|
| Ruff      | Linting + import sort | `uv run ruff check .`      |
| Black     | Formatting            | `uv run black .`           |
| MyPy      | Static type checking  | `uv run mypy`              |
| Pytest    | Tests + coverage      | `uv run pytest`            |

All tool configuration lives in [`pyproject.toml`](pyproject.toml) — there is
no separate `setup.py`/`setup.cfg`; `pyproject.toml` is the single source of
truth for build and tool configuration (PEP 517/518/621).

## Modules

- **Module 1 — BTSnoop HCI parser** ([docs/hci_parser.md](docs/hci_parser.md)):
  parses `btsnoop_hci.log` into `HciPacket` objects (timestamp, direction,
  size, sequence number, packet type, and ACL connection handles/flags).
- **Module 2 — ATT parser** ([docs/att_parser.md](docs/att_parser.md)):
  decodes ATT PDUs (Exchange MTU, Read/Write Request/Response, Write
  Command, Notification, Indication, and GATT discovery responses) out of
  `HciPacket` objects.
- **Module 3 — GATT analyzer** (`analyzers.gatt`): reconstructs the
  services/characteristics/descriptors hierarchy (UUIDs, handles,
  properties) from GATT discovery PDUs.
- **Module 4 — Protocol analyzer** (`analyzers.protocol`): heuristically
  classifies ATT traffic (authentication/telemetry/configuration/heartbeat/
  firmware/unknown) with a confidence score per classification.
- **Capture report exporter** (`exporters.capture_report`): runs the full
  pipeline and writes `commands.csv`, `notifications.csv`,
  `statistics.json`, and `summary.md`.
- **Desktop GUI** (`gui`, PySide6): drag-and-drop a capture onto the window
  (or `File > Open`) to get a searchable/filterable packet table, a
  click-to-seek timeline, Hex/ASCII/Statistics panes for the selected
  packet, and a dark theme. The `File` menu also has `Export Report...` and
  `Compare with...` (wired to the exporter/comparator below), a persisted
  Recent Captures list, and keyboard shortcuts (Ctrl+O/E/Shift+C/F/Q).
- **Module 6 — Capture comparator** (`analyzers.compare`): diffs the
  notified values of two captures of the same device by GATT attribute
  handle, and heuristically guesses which changed handle maps to battery /
  voltage / temperature / GPS / ride mode / charging (confidence-scored,
  never asserted as fact).
- **Module 10 — Live BLE client** (`live`, Bleak): connects to a real RV400
  (scans by advertised name or a known address), discovers services,
  subscribes to every notify-capable characteristic, implements the PAIR
  handshake's mechanics (caller supplies the token — never derived or
  guessed), reconnects automatically on drop, and logs/saves/calls back
  every notification and write verbatim — no telemetry interpretation here.
  CLI: `revolt-ble-live`.
- **Module 11 — Flutter SDK** ([flutter_sdk/](flutter_sdk/), Dart/`flutter_blue_plus`):
  the mobile-side equivalent of Module 10 — `RevoltBleClient` with
  `connect()`/`authenticate()`/`listen()`/`write()`/`disconnect()`, same
  protocol, same raw-packets-only rule. Separate package/ecosystem (its own
  `pubspec.yaml`), not part of the Python distribution.
  [`flutter_sdk/example/`](flutter_sdk/example/) is a runnable dark-themed
  demo app: connect/disconnect, a live packet counter, and a scrolling raw
  notification log (timestamp, characteristic, hex, ASCII per packet).

## Roadmap

See [ROADMAP.md](ROADMAP.md) for direction and [REMAINING_TASKS.md](REMAINING_TASKS.md)
for the concrete, estimated backlog.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the PR process and
[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for setup/conventions. Please also
read the [Code of Conduct](CODE_OF_CONDUCT.md). Every push/PR is scanned for
secrets with Gitleaks — see [SECRETS_POLICY.md](SECRETS_POLICY.md). Found a
security issue? See [SECURITY.md](SECURITY.md) instead of opening a public issue.

## License

MIT — see [LICENSE](LICENSE).
