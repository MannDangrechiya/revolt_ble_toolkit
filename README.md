# Revolt BLE Toolkit

A professional toolkit for reverse engineering Bluetooth Low Energy (BLE) traffic
captured in **Android HCI Snoop Logs**.

> **Status:** Foundation + Module 1 (BTSnoop HCI parser). Analysis above the
> HCI layer (L2CAP/ATT/GATT) and export business logic are intentionally
> **not** implemented yet and will land in later milestones.

## Requirements

- Python **3.12**
- [uv](https://docs.astral.sh/uv/) (preferred) or `pip`

## Project layout

```
revolt_ble_toolkit/
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
│       ├── cli/               # CLI wiring only — no business logic
│       │   └── main.py
│       ├── config/            # Layered settings (dataclasses) + logging setup
│       │   ├── settings.py
│       │   └── logging_config.py
│       ├── core/               # Domain layer: models, enums, exceptions, interfaces
│       │   ├── models.py
│       │   ├── enums.py
│       │   ├── exceptions.py
│       │   └── interfaces.py
│       ├── parsers/            # Capture-log parsers
│       │   ├── base.py         # Generic extension point (future pipeline use)
│       │   └── btsnoop/        # Module 1: BTSnoop HCI parser
│       │       ├── constants.py
│       │       ├── models.py
│       │       └── parser.py
│       ├── analyzers/          # Extension point for record analyzers
│       │   └── base.py
│       ├── exporters/          # Extension point for result exporters
│       │   └── base.py
│       └── utils/              # Small, dependency-free helpers
├── docs/
│   └── hci_parser.md         # Module 1 documentation
└── tests/
    ├── test_config/
    ├── test_core/
    └── test_parsers/
```

## Architecture

The toolkit is organized around a small domain layer (`core`) that defines
**interfaces** (`LogParser`, `PacketAnalyzer`, `ResultExporter`) and **models**
(`CaptureFile`, `ParsedRecord`, `AnalysisResult`) as immutable dataclasses.
Concrete implementations live in dedicated packages (`parsers`, `analyzers`,
`exporters`) and depend on `core`, never the other way around — this keeps the
domain layer stable while implementations can be added freely
(Dependency Inversion / Open-Closed principles).

Each extension-point package ships a `base.py` with an abstract base class
(`BaseLogParser`, `BaseAnalyzer`, `BaseExporter`) for future pipeline
integration. The first concrete parser, `BtSnoopHciParser`, is built
standalone against its own rich, typed models (`HciPacket`, `AclHeader`)
rather than forced through the generic `ParsedRecord` envelope, since
nothing consumes that generic path yet — see
[`docs/hci_parser.md`](docs/hci_parser.md).

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
```

### With pip

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
pytest
revolt-ble-toolkit --help
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

## Roadmap (future milestones)

- L2CAP / ATT / GATT decoding of ACL payloads
- BLE packet/PDU analysis (advertising, pairing, etc.)
- Export formats (JSON, CSV, PCAP)
- CLI subcommand implementations
