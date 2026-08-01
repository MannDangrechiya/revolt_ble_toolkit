# Known Limitations

## Protocol Confidence Levels

Everything this toolkit knows about the RV400's actual protocol (as opposed to generic Bluetooth/GATT wire format) falls into exactly three tiers. Nothing is presented as more certain than this table says.

### Confirmed (directly observed in a real capture, or defined by the Bluetooth Core Specification itself)

| Item | Evidence |
|---|---|
| BTSnoop file format (byte order, epoch offset, record framing) | Bluetooth/Android public specification, not device-specific. |
| ATT/GATT wire format (opcodes, discovery PDU shapes, lockstep request/response) | Bluetooth Core Specification, not device-specific. |
| Service `49535343-fe7d-4ae5-8fa9-9fafd205e455` (handles 80–88) carries the vehicle's command/response traffic | Directly observed in the analyzed RV400 capture: `analyzers.gatt` discovery output, re-verified twice independently in this project (once when the capture was first analyzed, again while building Module 10). |
| Characteristic `49535343-1e4d-4bd9-ba61-23c647249616` (value_handle 82, WRITE\|NOTIFY) is the specific command/response channel, not the *other* write+notify characteristic in the same service (handle 87) | Directly observed: this exact handle carried the `PAIR...#`/`ACCEPTED`/`LD,...`/`VS,ON`/`VS,OFF` traffic in the analyzed capture; handle 87 was structurally present but never seen carrying traffic. |
| The literal bytes `PAIR<token>#` are written to initiate pairing, and `ACCEPTED` is the literal success response | Directly observed in `commands.csv`/`notifications.csv` from the analyzed capture. |
| Device Information service (handles 89–105) exposes standard characteristics (Firmware Revision, Software Revision, Manufacturer Name, etc.) | Directly observed via GATT discovery. Their *values* were never read/decoded by this toolkit — only their presence and handles are confirmed. |

### Likely (heuristic, confidence-scored, never asserted as fact)

| Item | Confidence | Basis |
|---|---|---|
| A given changed handle's value represents battery / voltage / temperature / GPS / ride mode / charging (Modules 4, 6) | 0.3–0.95, varies per match — see `analyzers.protocol.analyzer`/`analyzers.compare.analyzer` docstrings for the exact decision list | Byte-pattern heuristics (numeric range, cardinality, structural shape) tuned against the one real capture available. Every result carries its own confidence and reason string — check them before trusting a specific classification. |
| The `LD,...` notification frame (comma-separated fields including what look like a device ID, coordinates, and a timestamp) is a structured telemetry record | Not scored — not decoded at all | Only one example instance was ever observed. That's not enough evidence to confidently determine field boundaries and meaning, so this toolkit deliberately does not attempt to parse it — see Module 2's `docs/att_parser.md` and this project's "never guess" rule. |

### Unknown (not attempted, and why)

| Item | Why it's not attempted |
|---|---|
| What the second write+notify characteristic (handle 87) in the Vehicle Control service is for | Never observed carrying traffic in the one capture analyzed. No evidence to reason from. |
| What the write-only characteristic (handle 85) is for | Same — never observed carrying traffic. |
| How the `PAIR<token>#` token itself is derived (IMEI-based? session-based? something else?) | Only one example token was ever observed; deriving an algorithm from a single sample would be pure speculation. The live client (Module 10) correctly treats this as an opaque, caller-supplied value rather than trying to generate it. |
| Field-by-field meaning of the `LD,...` telemetry frame | See "Likely," above — one sample isn't enough evidence. |
| Whether any of the above holds on a different RV400 unit or firmware revision | Only one device was ever captured. Everything above is scoped to that one unit until a second capture (ideally from a different unit) confirms or contradicts it. |

## Other Limitations

- **No real-hardware validation of the live BLE client this audit.** Tested against a fake Bleak backend built from the real, installed `bleak` 3.0.2's actual source (not assumed from memory) — this validates logic, not real radio behavior. See REMAINING_TASKS.md, High priority item 1.
- **Large-capture memory use is untested.** The pipeline fully materializes a capture into memory. Fine for every capture actually tested (thousands of packets, sub-second); unverified for anything gigabyte-scale. See REMAINING_TASKS.md, Medium priority item 3.
- **GUI coverage gaps are visual/interaction code, not logic gaps.** `gui/main_window.py` (81%) and `gui/widgets.py` (86%) have real, working features (drag-drop, search, filter, timeline, hex/ASCII, statistics) — the uncovered lines are Qt paint events, mouse events, and drag-and-drop event handlers that aren't meaningfully unit-testable without a running display. The underlying logic they call (filtering, formatting) is separately tested and at 100%.
- **No Android runtime permission flow in the Flutter demo.** Manifest permissions are declared (required for the OS to allow granting them at all), but the demo doesn't prompt at runtime — explicitly out of scope for this audit per the instructions not to modify the Flutter application.
- **The `flutter_sdk/` package was not audited in this pass.** Explicitly excluded per instructions. Its own `README.md`/`CHANGELOG.md` are the source of truth for its state.
