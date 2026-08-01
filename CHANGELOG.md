# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/); this project uses semantic versioning once tagged (see `VERSION`).

## [1.0.0] — 2026-08-01

First tagged release. Everything below was built incrementally across one continuous session and is being recorded here as a single release rather than a series of pre-1.0 tags.

### Added

- **Project foundation:** Python 3.12 project layout, `pyproject.toml` (Ruff/Black/MyPy/pytest config), layered configuration system (`config.settings`), package-root logging.
- **Module 1 — BTSnoop HCI parser:** `parsers.btsnoop.BtSnoopHciParser`, parsing Android `btsnoop_hci.log` into `HciPacket` objects (timestamp, direction, size, sequence number, packet type, ACL connection handles/flags).
- **Module 2 — ATT parser:** `parsers.att.AttParser`, decoding Exchange MTU, Read/Write Request/Response, Write Command, Notification, Indication, and GATT-discovery response PDUs.
- **Module 3 — GATT analyzer:** `analyzers.gatt.GattAnalyzer`, reconstructing the services/characteristics/descriptors hierarchy from discovery PDUs.
- **Module 4 — Protocol analyzer:** `analyzers.protocol.ProtocolAnalyzer`, heuristic confidence-scored classification of ATT traffic by role.
- **Capture report exporter:** `exporters.capture_report.generate_capture_report`, writing `commands.csv`/`notifications.csv`/`statistics.json`/`summary.md`.
- **Desktop GUI:** PySide6 app (`revolt-ble-gui`) — drag-and-drop, searchable/filterable packet table, click-to-seek timeline, Hex/ASCII/Statistics panes, dark theme, `File` menu (Export Report..., Compare with..., a `QSettings`-backed Recent Captures list, Quit), and keyboard shortcuts (Ctrl+O/E/Shift+C/F/Q).
- `analyzers.compare.format_diff_report`: plain-text rendering of a comparator's `HandleDiff` list, shared by the CLI's `compare` subcommand and the GUI's Compare with... dialog rather than each formatting it separately.
- **Module 6 — Capture comparator:** `analyzers.compare.compare_captures`, diffing two captures by GATT attribute handle and heuristically correlating changes to battery/voltage/temperature/GPS/ride-mode/charging.
- **Module 10 — Live BLE client:** `live.RevoltLiveClient` (Bleak-based), `revolt-ble-live` CLI — scan, connect, discover, subscribe, PAIR handshake, write, auto-reconnect, raw notification/write logging and persistence.
- **Module 11 — Flutter SDK:** separate Dart package (`flutter_sdk/`) mirroring the live client for mobile use, plus a runnable demo app (`flutter_sdk/example/`).
- **CLI:** `revolt-ble-toolkit parse|analyze|export|compare` — previously a stub, now fully wired to the pipeline, exporter, and comparator (see Fixed, below).

### Fixed (v1.0 production-readiness audit)

- `GattAnalyzer._parse_services`/`_parse_characteristics` no longer crash with an unhandled `struct.error` on a malformed capture that declares a discovery-entry length shorter than its fixed fields require; the malformed response is now logged and skipped, matching the existing truncated-ACL-header handling.
- `ConfigurationError` is now actually raised (wrapping `tomllib.TOMLDecodeError`) when a config file has invalid TOML, instead of a raw, unhelpful exception.
- `ExportError` is now actually raised (wrapping `OSError`) when a report file or its output directory can't be written.
- The CLI's `parse`/`analyze`/`export` subcommands, previously 100% placeholder ("not implemented yet" log lines with 0% test coverage), now do real work; a `compare` subcommand was added.

### Changed

- `core` is now just the exception hierarchy. Previously it also held a generic parser/analyzer/exporter interface layer (`LogParser`/`PacketAnalyzer`/`ResultExporter` Protocols, `BaseLogParser`/`BaseAnalyzer`/`BaseExporter` ABCs, generic `CaptureFile`/`ParsedRecord`/`AnalysisResult` models) that no concrete module ever adopted — removed rather than kept as unused abstraction (see ARCHITECTURE.md).

### Removed

- `core.interfaces`, `core.models`, `core.enums`, `parsers.base`, `analyzers.base`, `exporters.base` — confirmed dead via direct usage search before removal, not assumed.
- `utils.paths` (`ensure_directory`, `project_root`) — never imported anywhere outside its own definition.
- `core.exceptions.AnalysisError` — defined, never raised or caught anywhere.
- The unreachable `Path` branch in `config.settings._coerce` — no env-overridable setting is `Path`-typed.

### Testing

- Test count: 120 (up from 100 before the audit's coverage pass). Line coverage: 91% overall (up from 86%).
- New coverage for: CLI subcommands (0% → 99%), malformed-TOML/env-var-override paths in configuration, the GATT analyzer's malformed-input guards, several previously-untested heuristic branches in the protocol analyzer and comparator.
