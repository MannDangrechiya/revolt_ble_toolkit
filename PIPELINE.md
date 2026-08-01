# Pipeline

The four analysis stages, and the one function that runs all of them:

```python
from revolt_ble_toolkit.pipeline import run_pipeline

result = run_pipeline("btsnoop_hci.log")
# result.hci_packets:  list[HciPacket]
# result.att_packets:  list[AttPacket]
# result.services:     list[Service]
# result.classified:   list[ClassifiedPacket]
```

## Stage 1 — BTSnoop → HciPacket (`parsers.btsnoop`)

`BtSnoopHciParser().parse_file(path)` reads the BTSnoop file header (big-endian, magic `b"btsnoop\x00"`), then streams 24-byte record headers + variable-length payloads. Each record becomes one `HciPacket`: sequence number, UTC timestamp (BTSnoop uses a non-Unix epoch — see `docs/hci_parser.md` for the exact conversion), direction (host↔controller), packet type (Command/ACL/SCO/Event/ISO, from the H4 framing byte), and — for ACL packets only — an `AclHeader` with the 12-bit connection handle and PB/BC flags.

**Not attempted:** ACL fragment reassembly. One ACL packet is assumed to be one complete L2CAP PDU, which holds for every packet type this toolkit currently decodes but would need addressing for very large reads/writes spanning multiple ACL packets.

## Stage 2 — HciPacket → AttPacket (`parsers.att`)

`AttParser().parse(hci_packets)` filters to ACL packets whose L2CAP channel ID is `0x0004` (the fixed ATT channel), decodes the L2CAP header (2-byte length + 2-byte CID, little-endian), and reads the first payload byte as the ATT opcode. Only opcodes the toolkit recognizes become `AttPacket`s (Exchange MTU, Read/Write Request/Response, Write Command, Notification, Indication, and the three GATT-discovery response types) — everything else is silently skipped, by design (see `docs/att_parser.md`).

`AttPacket.attribute_handle`/`.value`/`.exchanged_mtu` are computed properties, not stored fields — they parse `parameters` differently per opcode (e.g. a Read Response has no handle of its own; a Notification's first two bytes are the handle, the rest is `.value`).

## Stage 3 — AttPacket → GATT hierarchy (`analyzers.gatt`)

`GattAnalyzer().analyze(att_packets)` groups the three GATT-discovery response opcodes by connection handle (attribute handles are only unique *per connection*, not globally), then nests characteristics inside the service whose handle range contains them, and descriptors inside the characteristic whose handle range precedes them. Produces `list[Service]`, each with a tuple of `Characteristic`, each with a tuple of `Descriptor`.

`handle_uuid_map(services)` flattens this into `{attribute_handle: uuid}` — the one piece of this stage's output that `analyzers.protocol`, `analyzers.compare`, and the CLI/GUI all reuse rather than recompute.

**Malformed input:** a discovery response that declares a per-entry length shorter than its fixed fields need is logged as a warning and the whole response is skipped (not raised) — this is exactly the crash bug this project's v1.0 audit found and fixed; see CHANGELOG.md.

## Stage 4a — Protocol classification (`analyzers.protocol`)

`ProtocolAnalyzer().classify(att_packets, services)` groups ATT traffic by `(connection_handle, attribute_handle)` "channel" (a Read Response has no handle of its own, so it's attributed to the most recent Read Request on that connection), then runs a priority-ordered decision list per channel: known GATT UUID (highest confidence) → behavioral heuristics (boolean toggle → charging; small discrete values → ride mode; 0–100 range → battery; signed 2-byte in Celsius range → temperature; 2-byte in millivolt/centivolt range → voltage; 4-byte float in lat/lon range → GPS) → `UNKNOWN`. Every `ClassifiedPacket` carries `(category, confidence, reason)` — never just a label.

## Stage 4b — Cross-capture comparison (`analyzers.compare`, optional second stage)

`compare_captures(path1, path2)` runs `run_pipeline` on *both* files, then `CaptureComparator().compare(result1, result2)` diffs each attribute handle's last notified value between the two captures and runs the same kind of known-UUID-then-heuristic decision list to guess what changed. Keyed by **attribute handle**, not connection handle — connection handles are assigned per-session by the controller and mean nothing across two independently-captured files; GATT attribute handles come from the peripheral's own fixed attribute table and stay stable across sessions.

## Consumers

- **CLI** (`revolt-ble-toolkit parse|analyze|export|compare`) calls each stage (or `run_pipeline` directly) and prints/writes the result — no logic of its own beyond argument parsing and output formatting.
- **GUI** (`revolt-ble-gui`) calls `run_pipeline` on drag-and-drop, then presents `result.classified` in a filterable table with a timeline and hex/ASCII/statistics panes.
- **Live client** (`revolt-ble-live`) does *not* use this pipeline at all — it talks to a real device over Bleak in real time and exposes raw notification/write events directly. It shares only the empirically-verified UUID constants and the project's "never guess" philosophy with the offline pipeline, not any code.
