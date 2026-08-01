# Remaining Tasks

Everything that could be fixed with code, in this audit, was fixed in this audit (see PROJECT_AUDIT.md's Weaknesses/Technical Debt sections and CHANGELOG.md). What's left below either needs something this session doesn't have access to (real hardware, more real captures) or is a genuine scope decision, not an oversight.

## Critical

**None.** The two genuinely critical issues found during this audit — a crash bug in `GattAnalyzer` on malformed discovery PDUs, and a CLI that was 100% unimplemented placeholder — were fixed as part of this same pass, not deferred. See PROJECT_AUDIT.md.

## High

### 1. Real-hardware validation of the live BLE client

- **Why it matters:** Module 10 (`live.RevoltLiveClient`) is the toolkit's only component that talks to a real device instead of a capture file. Everything else in the project can be, and was, fully verified against real capture data or synthetic fixtures. This one component's correctness ultimately depends on how a real Bluetooth adapter and a real RV400 actually behave — which a test suite, however thorough, can only approximate.
- **Current limitation:** Tested against a hand-built fake of Bleak's API (`_FakeClient`/`_FakeScanner` in `tests/test_live/test_client.py`), built by installing the real `bleak` 3.0.2 and reading its actual source rather than assuming an API shape from memory. This validates the client's *logic* (control-characteristic selection, PAIR handshake state machine, reconnect-until-success) precisely. It cannot validate real BLE timing, real disconnect/reconnect behavior under actual radio conditions, or whether the empirically-recorded service/characteristic UUIDs still hold on a different firmware revision.
- **Recommended implementation:** Run `revolt-ble-live --pair <token>` against a real RV400 with a real Bluetooth adapter; confirm connect → discover → subscribe → pair → notification flow end to end; confirm reconnect actually recovers after physically power-cycling the vehicle or walking out of range.
- **Estimated effort:** 1–2 hours, once hardware is available.
- **Dependencies:** A physical Bluetooth adapter and access to the RV400 (or another device using the same protocol).

### 2. More real captures to validate protocol-classification accuracy

- **Why it matters:** Modules 4 (`ProtocolAnalyzer`) and 6 (`CaptureComparator`) classify traffic using byte-pattern heuristics (battery-range bytes, voltage-range 2-byte values, GPS-range floats, etc.) tuned against one real capture of one device. The code is fully tested — every heuristic branch has a passing test — but "does this heuristic correctly identify battery telemetry on a *different* RV400, or a different firmware version" is an empirical question a unit test can't answer.
- **Current limitation:** All known-UUID mappings (battery, temperature) and all byte-pattern heuristics were derived from a single capture. The known-UUID table only covers what was actually observed; a device that also exposes, say, GATT Heart Rate Service would be classified `UNKNOWN`, correctly, not incorrectly guessed at.
- **Recommended implementation:** Capture the same vehicle in more states (charging vs. not, moving vs. stationary, different ride modes) and, separately, capture a second unit if available. Compare `ProtocolAnalyzer`'s output against what you independently know was happening at capture time; tighten or loosen heuristic thresholds based on real mismatches, not speculation.
- **Estimated effort:** Ongoing — a few hours per new capture reviewed.
- **Dependencies:** Access to the vehicle in varied real-world states.

## Medium

### 3. Streaming/lazy pipeline for very large captures

- **Why it matters:** `pipeline.run_pipeline()` calls `list(...)` on the HCI parser's generator immediately, and every downstream stage (ATT, GATT, protocol classification) takes a fully-materialized list. This is simple and was measured (not assumed) to be the right call for the captures actually tested.
- **Measured, not guessed:** profiled against a synthetic, reproducible 174.7 KiB / 4,706-packet capture — full pipeline 72–122 ms across 3 runs, peak memory a stable 3.11 MiB, no disproportionate hotspot (HCI parsing and export dominate the total simply because they touch every byte/write every file). Linearly extrapolating to a 1 GiB capture: ~12 minutes, ~18 GiB peak memory — the scale at which this would start to genuinely matter. See KNOWN_LIMITATIONS.md for the full numbers and methodology.
- **Current limitation:** No streaming path exists. `GattAnalyzer` and `ProtocolAnalyzer` both need to see a channel's/connection's *entire* history to do cross-packet analysis (heartbeat-interval detection, discovery-response correlation across a whole file), so full streaming isn't a drop-in change — it would need each analyzer's internal accumulation logic reworked to bound memory, not just the parser's output.
- **Recommended implementation:** Only worth doing once a real capture actually approaches the ~1 GiB scale above. If it is: re-profile that specific file first, then consider chunked/windowed analysis in `GattAnalyzer`/`ProtocolAnalyzer` rather than a full pipeline rewrite.
- **Estimated effort:** 1–2 days, and carries real regression risk against a currently fully-green, 100%-covered pipeline — don't take this on speculatively.
- **Dependencies:** A real capture large enough to demonstrate the problem exists before spending the effort.

### 4. PCAP/PCAPNG export

- **Why it matters:** Would let captures be opened directly in Wireshark with its BLE/ATT dissectors, which is a natural complementary view to this toolkit's own CSV/JSON/Markdown output.
- **Current limitation:** `exporters.capture_report` only writes CSV/JSON/Markdown; there's no PCAP writer.
- **Recommended implementation:** A pcap writer for raw HCI records is genuinely simple (stdlib `struct`, no new dependency needed — pcap's own format is not much more than BTSnoop's). Write raw `HciPacket.data` bytes with a DLT_BLUETOOTH_HCI_H4 link type.
- **Estimated effort:** ~half a day including tests.
- **Dependencies:** None.

## Low

### 5. GATT characteristic *value* semantics (e.g., what a CCCD's bits mean)

- **Why it matters:** Would let the toolkit describe *what a write to a given descriptor does*, not just that a write happened.
- **Current limitation:** Deliberately not implemented — this is the same "don't guess protocol data" boundary the whole project has held since Module 1. A CCCD's two bytes (`0x0001` = notifications, `0x0002` = indications, per the Bluetooth Core Spec) could be decoded generically, but *device-specific* descriptor/characteristic value meaning cannot be inferred without a spec or more targeted captures.
- **Recommended implementation:** The *standard* CCCD bit meanings could be added now (they're Bluetooth-Core-Spec-defined, not device-specific — this is one case where "confirmed by the spec itself" is a legitimate evidence tier, distinct from guessing). Anything device-specific stays deferred until backed by a capture that demonstrates it.
- **Estimated effort:** ~2 hours for the spec-defined CCCD case only.
- **Dependencies:** None for the CCCD case; real captures for anything device-specific.

### 8. Additional known-UUID entries for Modules 4/6

- **Why it matters:** More Bluetooth SIG-assigned UUIDs recognized directly (high confidence) instead of falling back to byte-pattern heuristics (lower confidence).
- **Current limitation:** The known-UUID tables only include what was actually observed (Battery Level, Temperature). Never expand from a public UUID list — only from a real captured device that actually exposes it.
- **Recommended implementation:** Add entries only as new real captures reveal new standard services in use.
- **Estimated effort:** Trivial per entry (a one-line addition + one test) once evidence exists.
- **Dependencies:** More real captures.

### 9. Flutter demo: Android runtime permission flow, app icons

- **Why it matters:** The demo app declares the Android manifest permissions needed for BLE, but doesn't prompt for them at runtime (Android 12+ requires an explicit runtime request for `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT`, not just the manifest declaration).
- **Current limitation:** Documented as a known gap when the demo was built; would need a `permission_handler` dependency and a request flow.
- **Recommended implementation / effort / dependencies:** Explicitly **out of scope for this audit** — the task instructions for this pass were to not modify the Flutter application. Left here only for completeness/traceability.
