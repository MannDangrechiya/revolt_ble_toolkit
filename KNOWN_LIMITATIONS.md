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
- **Large-capture memory use — measured, not guessed, and genuinely fine at every size tested.** The pipeline fully materializes a capture in memory rather than streaming. Re-measured for the v1.0 release audit against a **synthetic, reproducible** 174.7 KiB / 4,706-packet capture generated with `tests/test_parsers/fixtures.py` (the previous version of this table was measured against a real personal device's bugreport capture that was never reproducible by another contributor and has since been removed from the project entirely — see CHANGELOG.md). Methodology: wall time is the best-of-5 across 3 separate process runs (with console logging disabled — logging I/O during a timed loop distorts the numbers exactly like `tracemalloc` does, see below); peak memory is from a separate `tracemalloc`-instrumented run, since profiling instrumentation itself measurably distorts timing if run in the same pass:

  | Stage | Wall time (range across 3 runs) |
  |---|---|
  | HCI parse (`BtSnoopHciParser`) | 40–64 ms |
  | ATT decode (`AttParser`) | 15–33 ms |
  | GATT discovery (`GattAnalyzer`) | 1–2 ms |
  | Protocol classification (`ProtocolAnalyzer`) | 16–31 ms |
  | **Full pipeline** (`run_pipeline`) | **72–122 ms** |
  | Full export (`generate_capture_report`, incl. all 4 files) | 113–164 ms |
  | Peak memory (full pipeline) | 3.11 MiB (stable across all 3 runs) |

  The run-to-run spread (up to ~2x) is real, disclosed variance from this being measured on an ordinary Windows development machine with background load, not a controlled benchmark rig — reporting a single overly-precise number here would be less honest than showing the range actually observed. HCI parsing and export still dominate the total, as expected (they touch every byte / write every file respectively), and peak memory is consistently low (~3 MiB) regardless of run-to-run wall-time noise. Linearly extrapolating the upper end of the full-pipeline range to a **1 GiB** capture: roughly **12 minutes** and **~18 GiB** peak memory — the point at which the current fully-in-memory design would start to genuinely matter. No capture anywhere near that size has ever been available to actually test against. See REMAINING_TASKS.md, Medium priority item 3.
- **GUI coverage gaps are almost entirely drag-and-drop glue, not untested interaction logic.** A pre-release independent audit found that the category-filter, row-selection, timeline-seek, and timeline-click handlers previously *claimed* to be "not meaningfully unit-testable without a running display" actually were testable — Qt's offscreen backend runs `mousePressEvent`/`paintEvent` correctly when fed a directly-constructed event, no real display needed. Tests were added; `gui/main_window.py` is now 95% (11 lines missing, down from 24: only `dragEnterEvent`/`dropEvent`, which genuinely do need a real OS drag session to simulate) and `gui/widgets.py` is 91% (12 lines missing, down from 19: `paintEvent`'s per-bucket drawing loop body is exercised but not every branch, plus one defensive dead-code line). `gui/app.py` (the dark-theme `QPalette` setup and `main()` entry point) still has **0% coverage** — real, working code (verified by direct read), but genuinely untested; there is no `tests/test_gui/test_app.py`. This is a real, disclosed gap, not a logic gap: the underlying formatting/filtering logic these UI layers call is separately tested and at 100%.
- **No Android runtime permission flow in the Flutter demo.** Manifest permissions are declared (required for the OS to allow granting them at all), but the demo doesn't prompt at runtime — explicitly out of scope for this audit per the instructions not to modify the Flutter application.
- **The `flutter_sdk/` package was not audited in this pass.** Explicitly excluded per instructions. Its own `README.md`/`CHANGELOG.md` are the source of truth for its state.
