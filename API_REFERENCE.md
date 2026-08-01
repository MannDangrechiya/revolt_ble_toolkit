# API Reference

The public surface of each top-level package, as actually exported by its `__init__.py` (not inferred — copied from the real `__all__` lists). Import from the package, not the submodule, unless you have a specific reason not to (e.g. `from revolt_ble_toolkit.parsers import BtSnoopHciParser`, not `from revolt_ble_toolkit.parsers.btsnoop.parser import BtSnoopHciParser`).

## `revolt_ble_toolkit.core`

```python
ToolkitError            # base class for every toolkit-specific error
ConfigurationError      # invalid/missing configuration (e.g. malformed TOML)
ParsingError            # a capture file is structurally broken
ExportError             # a report file couldn't be written
LiveClientError         # BLE connection/discovery/pairing failure
```

## `revolt_ble_toolkit.config`

```python
AppSettings             # frozen dataclass: environment, debug, paths, logging
PathSettings            # frozen dataclass: project_root, data_dir, log_dir, reports_dir
LoggingSettings          # frozen dataclass: level, format, rotation
get_settings(config_path: Path | None = None) -> AppSettings   # cached singleton
```

`revolt_ble_toolkit.config.logging_config` (imported directly, not re-exported at the package level):

```python
get_logger(name: str) -> logging.Logger
configure_logging(settings: AppSettings | None = None) -> None
```

## `revolt_ble_toolkit.parsers`

```python
BtSnoopHciParser         # .parse_file(path) -> Iterator[HciPacket]; .read_header(path)
HciPacket                # frozen dataclass: number, timestamp, direction, packet_type, acl, ...
AclHeader                # frozen dataclass: connection_handle, packet_boundary_flag, ...
HciPacketType            # enum: COMMAND, ACL_DATA, SCO_DATA, EVENT, ISO_DATA, UNKNOWN
PacketDirection          # enum: HOST_TO_CONTROLLER, CONTROLLER_TO_HOST
BtSnoopFileHeader        # frozen dataclass: identification, version, datalink_type

AttParser                # .parse(hci_packets) -> Iterator[AttPacket]
AttPacket                # frozen dataclass + .attribute_handle/.value/.exchanged_mtu properties
AttOpcode                # enum: EXCHANGE_MTU_REQUEST/RESPONSE, READ_REQUEST, READ_RESPONSE,
                         #   WRITE_REQUEST, WRITE_COMMAND, HANDLE_VALUE_NOTIFICATION/INDICATION,
                         #   READ_BY_GROUP_TYPE_RESPONSE, READ_BY_TYPE_RESPONSE,
                         #   FIND_INFORMATION_RESPONSE
```

## `revolt_ble_toolkit.analyzers`

```python
GattAnalyzer             # .analyze(att_packets) -> list[Service]
Service                  # frozen dataclass: connection_handle, start/end_handle, uuid, characteristics
Characteristic           # frozen dataclass: declaration/value_handle, uuid, properties, descriptors
Descriptor               # frozen dataclass: handle, uuid
CharacteristicProperty   # IntFlag: BROADCAST, READ, WRITE, WRITE_WITHOUT_RESPONSE, NOTIFY, ...

ProtocolAnalyzer         # .classify(att_packets, services) -> list[ClassifiedPacket]
ClassifiedPacket         # frozen dataclass: packet, category, confidence, reason
PacketCategory           # enum: authentication, telemetry, configuration, heartbeat, firmware, unknown
generate_report(classified: Sequence[ClassifiedPacket]) -> str

CaptureComparator        # .compare(result1, result2) -> list[HandleDiff]
compare_captures(path1, path2) -> list[HandleDiff]
HandleDiff               # frozen dataclass + .changed_byte_offsets property
CorrelationCategory      # enum: battery, voltage, temperature, gps, ride_mode, charging, unknown
```

## `revolt_ble_toolkit.exporters`

```python
generate_capture_report(btsnoop_path, out_dir) -> CaptureReportPaths
CaptureReportPaths       # frozen dataclass: commands_csv, notifications_csv, statistics_json, summary_md
PipelineResult           # re-exported from pipeline — see below
build_statistics(btsnoop_path, result) -> dict[str, Any]
run_pipeline(btsnoop_path) -> PipelineResult
```

## `revolt_ble_toolkit.pipeline`

```python
run_pipeline(btsnoop_path: str | Path) -> PipelineResult
build_statistics(btsnoop_path, result: PipelineResult) -> dict[str, Any]
PipelineResult           # frozen dataclass: hci_packets, att_packets, services, classified
```

## `revolt_ble_toolkit.live` (optional `live` extra)

```python
RevoltLiveClient(
    name_filter: str = "RV400",
    save_path: str | Path | None = None,
    on_notification: Callable[[NotificationEvent], None] | None = None,
    on_write: Callable[[WriteEvent], None] | None = None,
)
# async methods: .scan(), .connect(address=None), .write(uuid, data), .authenticate(token),
#                .disconnect()
# properties: .is_connected, .control_characteristic_uuid

NotificationEvent        # frozen dataclass: timestamp, characteristic_uuid, value
WriteEvent               # frozen dataclass: timestamp, characteristic_uuid, value
```

## `revolt_ble_toolkit.cli.main`

```python
main(argv: Sequence[str] | None = None) -> int    # entry point for `revolt-ble-toolkit`
build_parser() -> argparse.ArgumentParser
```

Subcommands: `parse <capture>`, `analyze <capture>`, `export <capture> [--out-dir DIR]`, `compare <capture1> <capture2>`.

## `revolt_ble_toolkit.gui`

No importable API beyond `gui.app.main()` (the `revolt-ble-gui` entry point) — this package is an application, not a library surface. See `MODULE_REFERENCE.md`.
