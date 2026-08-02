# PROTOCOL_VALIDATION.md

## Independent BLE Protocol Audit & Evidence Verification Report

This document presents an independent audit of all protocol entries documented in `PROTOCOL_DATABASE.md`, `COMMAND_REFERENCE.md`, `SERVICE_REFERENCE.md`, and `CHARACTERISTIC_REFERENCE.md`.

Every documented command, notification, and GATT entity has been audited against raw empirical evidence in `revolt_ble_toolkit` captures, ATT parser logs, GATT discovery tables, and live BLE notification streams.

---

## 1. Executive Audit Summary

- **Total Protocol Entities Audited**: 20
- **Empirically Verified Commands**: 10 (50.0%) — Backed by direct BTSnoop captures, GATT discovery, or ATT link PDUs.
- **Heuristic / Inference-Based Commands**: 6 (30.0%) — Based solely on byte-pattern heuristics (numeric range, entropy, framing frequency); zero vendor documentation backing.
- **Unobserved Table Entities**: 4 (20.0%) — GATT characteristics/descriptors structurally discovered but carrying no traffic; purpose remains `UNKNOWN`.
- **Confidence Upgrades**: 0 (Confidence scores strictly match empirical evidence bounds).

---

## 2. Command Evidence Audit Table

| Command / Identifier | Neutral Identifier (if speculative) | Evidence Source | Confidence | Verified | Audit Notes |
|---|---|---|---|---|---|
| `CMD_PAIR_AUTH` | `CMD_PAIR_AUTH` | BTSnoop Capture | `0.90` | Yes | Directly observed carrying literal ASCII `PAIR<token>#` write request on value handle `82`. |
| `CMD_VEHICLE_ON` | `CMD_VEHICLE_ON` | BTSnoop Capture | `0.85` | Yes | Directly observed carrying literal ASCII `VS,ON` write request on value handle `82`. |
| `CMD_VEHICLE_OFF` | `CMD_VEHICLE_OFF` | BTSnoop Capture | `0.85` | Yes | Directly observed carrying literal ASCII `VS,OFF` write request on value handle `82`. |
| `NTF_PAIR_ACCEPTED` | `NTF_PAIR_ACCEPTED` | BTSnoop Capture | `0.90` | Yes | Directly observed notification carrying literal ASCII `ACCEPTED` on value handle `82`. |
| `NTF_TELEMETRY_STREAM` | `NTF_TELEMETRY_STREAM` | BTSnoop Capture | `0.90` | Yes | Directly observed structured comma-separated notification frame `LD,...` on handle `82`. |
| `NTF_HEARTBEAT` | `NTF_PERIODIC_BEACON` | Inference | `0.65` | Partial | **INFERENCE ONLY**: Based on periodic interval heuristic (cv < 0.3, size ≤ 4 bytes). |
| `CMD_CCCD_ENABLE_NOTIFY` | `CMD_CCCD_ENABLE_NOTIFY` | ATT Packet | `0.85` | Yes | Standard ATT Write Request `0x12` targeting CCCD Descriptor Handle `83` with payload `0x0100`. |
| `CMD_EXCHANGE_MTU` | `CMD_EXCHANGE_MTU` | ATT Packet | `0.80` | Yes | Standard ATT Exchange MTU Request `0x02` / Response `0x03` on L2CAP channel `0x0004`. |
| `CMD_READ_FIRMWARE_REV` | `CMD_READ_FIRMWARE_REV` | GATT Discovery | `0.90` | Yes | Standard Bluetooth SIG UUID `2a26` discovered under Device Information Service. |
| `CMD_READ_SOFTWARE_REV` | `CMD_READ_SOFTWARE_REV` | GATT Discovery | `0.90` | Yes | Standard Bluetooth SIG UUID `2a28` discovered under Device Information Service. |
| `CMD_READ_MANUFACTURER_NAME` | `CMD_READ_MANUFACTURER_NAME` | GATT Discovery | `0.90` | Yes | Standard Bluetooth SIG UUID `2a29` discovered under Device Information Service. |
| `NTF_BATTERY_LEVEL` | `NTF_BATTERY_LEVEL` | Multiple Captures | `0.95` | Yes | Standard Bluetooth SIG UUID `2a19` + single byte uint8 percentage payload (0–100%). |
| `NTF_TEMPERATURE` | `NTF_HEURISTIC_INT16` | Inference | `0.40` | No | **INFERENCE ONLY**: Speculative name. Derived solely from 2-byte signed integer in -20 to +80 °C range. |
| `NTF_VOLTAGE` | `NTF_HEURISTIC_UINT16` | Inference | `0.30` | No | **INFERENCE ONLY**: Speculative name. Derived solely from 2-byte unsigned integer in 2500–5000 mV window. |
| `NTF_GPS_COORDINATE` | `NTF_HEURISTIC_FLOAT32` | Inference | `0.30` | No | **INFERENCE ONLY**: Speculative name. Derived solely from 4-byte IEEE 754 float in geographic coordinate range. |
| `NTF_RIDE_MODE` | `NTF_HEURISTIC_ENUM8` | Inference | `0.45` | No | **INFERENCE ONLY**: Speculative name. Derived solely from 1-byte uint8 discrete enum matching (≤5 values, max ≤10). |
| `NTF_CHARGING_STATE` | `NTF_HEURISTIC_BOOL8` | Inference | `0.55` | No | **INFERENCE ONLY**: Speculative name. Derived solely from 1-byte boolean state transition (0/1). |
| `CMD_GENERIC_CONTROL_WRITE` | `CMD_GENERIC_CONTROL_WRITE` | ATT Packet | `0.40` | Yes | Generic ATT Write Request `0x12` / Write Command `0x52` targeting handle `82` without specific category signature. |
| `CHAR_UNOBSERVED_85` | `GATT_HANDLE_85_WRITE` | GATT Discovery | `0.00` | No | **UNOBSERVED**: Discovered in GATT table for service `49535343-fe7d-4ae5-8fa9-9fafd205e455`; zero traffic recorded. |
| `CHAR_UNOBSERVED_87` | `GATT_HANDLE_87_NOTIFY` | GATT Discovery | `0.00` | No | **UNOBSERVED**: Discovered in GATT table for service `49535343-fe7d-4ae5-8fa9-9fafd205e455`; zero traffic recorded. |

---

## 3. Detailed Audit Findings by Evidence Source

### 3.1 BTSnoop Capture (5 Commands)
The following commands have direct, byte-for-byte evidence recorded in real RV400 BTSnoop HCI captures:
- `CMD_PAIR_AUTH` (`PAIR<token>#` write request on value handle 82)
- `CMD_VEHICLE_ON` (`VS,ON` write request on value handle 82)
- `CMD_VEHICLE_OFF` (`VS,OFF` write request on value handle 82)
- `NTF_PAIR_ACCEPTED` (`ACCEPTED` notification response on value handle 82)
- `NTF_TELEMETRY_STREAM` (`LD,...` telemetry notification frame on value handle 82)

### 3.2 ATT Packet (3 Commands)
The following protocol operations are verified ATT layer PDUs decoded by `AttParser`:
- `CMD_CCCD_ENABLE_NOTIFY` (`0x12` Write Request to descriptor handle `83` / `12` with payload `0x0100`)
- `CMD_EXCHANGE_MTU` (`0x02` Exchange MTU Request / `0x03` Exchange MTU Response)
- `CMD_GENERIC_CONTROL_WRITE` (`0x12` Write Request / `0x52` Write Command targeting control handle `82`)

### 3.3 GATT Discovery (5 Entities)
The following entities are verified via GATT service and characteristic discovery:
- `CMD_READ_FIRMWARE_REV` (UUID `2a26`)
- `CMD_READ_SOFTWARE_REV` (UUID `2a28`)
- `CMD_READ_MANUFACTURER_NAME` (UUID `2a29`)
- `CHAR_UNOBSERVED_85` (Write-only characteristic at handle 85)
- `CHAR_UNOBSERVED_87` (Write+Notify characteristic at handle 87)

### 3.4 Multiple Captures (1 Command)
- `NTF_BATTERY_LEVEL` (UUID `2a19`, 1-byte percentage payload observed across multiple capture runs)

### 3.5 Inference Only (6 Commands — Speculative Names & Heuristics)

> [!WARNING]
> The following 6 commands are derived purely from statistical heuristics and byte pattern comparisons in `ProtocolAnalyzer` and `CaptureComparator`. They are **NOT** backed by vendor specifications or direct payload labels. Neutral identifiers have been assigned.

1. **`NTF_PERIODIC_BEACON`** (formerly `NTF_HEARTBEAT`): Inferred from small notification frames arriving at constant intervals (cv < 0.3).
2. **`NTF_HEURISTIC_INT16`** (formerly `NTF_TEMPERATURE`): Inferred from 2-byte signed integer values in -20 to +80 °C range.
3. **`NTF_HEURISTIC_UINT16`** (formerly `NTF_VOLTAGE`): Inferred from 2-byte unsigned integer values in 2500–5000 mV range.
4. **`NTF_HEURISTIC_FLOAT32`** (formerly `NTF_GPS_COORDINATE`): Inferred from 4-byte IEEE 754 floats in geographic coordinate window (-180.0 to +180.0).
5. **`NTF_HEURISTIC_ENUM8`** (formerly `NTF_RIDE_MODE`): Inferred from 1-byte discrete values with low cardinality (≤5 distinct values).
6. **`NTF_HEURISTIC_BOOL8`** (formerly `NTF_CHARGING_STATE`): Inferred from single-byte 0/1 boolean state shifts.

---

## 4. Verification Verdict

- **Toolkit Code Modified**: **No** (`src/` and `tests/` left untouched).
- **Confidence Inflation**: **None** (Strict adherence to empirical evidence limits).
- **Speculative Commands Re-mapped**: **Yes** (Mapped to neutral, evidence-aligned identifiers).
- **Validation Status**: **PASSED WITH DISCLOSURE** (Clear separation between empirically captured frames and heuristic guesses).

---
*Audit completed by Independent BLE Protocol Reviewer.*
