# Module Reference

One entry per module: what it does, its key types, and where to look for more detail.

## `parsers.btsnoop` — Module 1

Parses Android BTSnoop capture files (`btsnoop_hci.log`) into `HciPacket` objects.

- **Entry point:** `BtSnoopHciParser().parse_file(path) -> Iterator[HciPacket]`
- **Key types:** `HciPacket` (timestamp, direction, packet type, size, ACL header), `AclHeader`, `HciPacketType`, `PacketDirection`
- **Tests:** `tests/test_parsers/test_btsnoop_parser.py`
- **Docs:** `docs/hci_parser.md`

## `parsers.att` — Module 2

Decodes ATT PDUs out of `HciPacket`s.

- **Entry point:** `AttParser().parse(hci_packets) -> Iterator[AttPacket]`
- **Key types:** `AttPacket` (opcode, `.attribute_handle`/`.value`/`.exchanged_mtu` computed properties), `AttOpcode`
- **Tests:** `tests/test_parsers/test_att_parser.py`
- **Docs:** `docs/att_parser.md`

## `analyzers.gatt` — Module 3

Reconstructs the GATT services/characteristics/descriptors hierarchy from ATT discovery PDUs.

- **Entry point:** `GattAnalyzer().analyze(att_packets) -> list[Service]`; `handle_uuid_map(services) -> dict[int, str]`
- **Key types:** `Service`, `Characteristic`, `Descriptor`, `CharacteristicProperty`
- **Tests:** `tests/test_analyzers/test_gatt_analyzer.py`

## `analyzers.protocol` — Module 4

Heuristically classifies ATT traffic by likely role. Confidence-scored, never asserted as fact.

- **Entry point:** `ProtocolAnalyzer().classify(att_packets, services) -> list[ClassifiedPacket]`; `generate_report(classified) -> str`
- **Key types:** `ClassifiedPacket` (packet, category, confidence, reason), `PacketCategory` (authentication/telemetry/configuration/heartbeat/firmware/unknown)
- **Tests:** `tests/test_analyzers/test_protocol_analyzer.py`

## `analyzers.compare` — Module 6

Diffs two captures of the same device by GATT attribute handle and heuristically correlates what changed.

- **Entry point:** `compare_captures(path1, path2) -> list[HandleDiff]`; `CaptureComparator().compare(result1, result2)`
- **Key types:** `HandleDiff` (attribute_handle, uuid, before/after values, `.changed_byte_offsets`, category, confidence, reason), `CorrelationCategory` (battery/voltage/temperature/gps/ride_mode/charging/unknown)
- **Formatting:** `format_diff_report(diffs) -> str` — plain-text rendering shared by the CLI's `compare` subcommand and the GUI's Compare with... dialog
- **Tests:** `tests/test_analyzers/test_compare_analyzer.py`

## `exporters.capture_report`

Runs the full pipeline and writes four files: `commands.csv`, `notifications.csv`, `statistics.json`, `summary.md`.

- **Entry point:** `generate_capture_report(btsnoop_path, out_dir) -> CaptureReportPaths`
- **Raises:** `ExportError` if the output directory/files can't be written
- **Tests:** `tests/test_exporters/test_capture_report.py`

## `pipeline`

Orchestrates the four stages above end to end. Shared by the CLI, GUI, exporter, and comparator so none of them re-implement the sequence.

- **Entry point:** `run_pipeline(btsnoop_path) -> PipelineResult`; `build_statistics(btsnoop_path, result) -> dict`
- **Key type:** `PipelineResult` (hci_packets, att_packets, services, classified)
- See PIPELINE.md for the full data flow.

## `gui` (optional `gui` extra: PySide6)

Desktop app: drag-and-drop a capture, get a searchable/filterable packet table, a click-to-seek timeline, Hex/ASCII/Statistics panes, dark theme, and a `File` menu (Open, Export Report..., Compare with..., a `QSettings`-backed Recent Captures list, Quit) plus keyboard shortcuts (Ctrl+O/E/Shift+C/F/Q).

- **Entry point:** `revolt-ble-gui [path/to/capture]` (console script) or `gui.app.main()`
- No progress bar/loading indicator: measured full-pipeline load time is ~27ms (see KNOWN_LIMITATIONS.md), so one would be unjustified theater rather than a real UX fix.
- **Tests:** `tests/test_gui/`

## `live` (optional `live` extra: Bleak) — Module 10

Live BLE client for a real device: scan, connect, discover, subscribe, PAIR handshake, write, auto-reconnect. Raw notifications only — no telemetry parsing.

- **Entry point:** `RevoltLiveClient(...)`; `revolt-ble-live` console script
- **Key types:** `NotificationEvent`, `WriteEvent`
- **Tests:** `tests/test_live/test_client.py` (against a verified fake of the real Bleak 3.0.2 API)

## `cli`

`revolt-ble-toolkit` console script: `parse`, `analyze`, `export`, `compare` subcommands, each a thin wrapper around the modules above.

- **Tests:** `tests/test_cli/test_main.py`

## `config`

Layered settings (`AppSettings`) and package-root logging setup, used by every other module.

- **Entry point:** `get_settings() -> AppSettings`; `get_logger(name) -> Logger`; `configure_logging(settings)`
- **Tests:** `tests/test_config/test_settings.py`

## `core`

The exception hierarchy shared by every module above: `ToolkitError` → `ParsingError`, `ConfigurationError`, `ExportError`, `LiveClientError`.

## `flutter_sdk/` (out of scope for the v1.0 Python-toolkit audit)

A separate Dart/Flutter package mirroring `live`'s client for mobile use, plus a runnable demo app under `flutter_sdk/example/`. Not part of the `revolt_ble_toolkit` Python distribution; see its own `README.md`.
