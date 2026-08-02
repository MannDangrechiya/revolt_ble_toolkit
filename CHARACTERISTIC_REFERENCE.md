# CHARACTERISTIC_REFERENCE.md

## Revolt RV400 BLE Characteristic Reference

This document provides a detailed specification for every GATT characteristic and descriptor discovered within the Revolt RV400 BLE protocol ecosystem using `revolt_ble_toolkit`.

---

## Characteristic Master Table

| Characteristic UUID | Value Handle | Service UUID | Properties | Format / Encoding | Functional Purpose | Confidence | Evidence & Reference |
|---|---|---|---|---|---|---|---|
| `49535343-1e4d-4bd9-ba61-23c647249616` | `82` | `49535343-fe7d-4ae5-8fa9-9fafd205e455` | `WRITE`, `NOTIFY` | ASCII Delimited / Hex Stream | **Primary Vehicle Control & Telemetry Channel** (`PAIR<token>#`, `VS,ON`, `VS,OFF`, `ACCEPTED`, `LD,...`) | `0.90` | Directly observed carrying all command and telemetry traffic in RV400 BTSnoop capture. |
| `UNOBSERVED_HANDLE_85` | `85` | `49535343-fe7d-4ae5-8fa9-9fafd205e455` | `WRITE` | UNKNOWN | Auxiliary Write Channel (No traffic observed) | `0.00` | GATT discovery table entry; zero traffic in captures. |
| `UNOBSERVED_HANDLE_87` | `87` | `49535343-fe7d-4ae5-8fa9-9fafd205e455` | `WRITE`, `NOTIFY` | UNKNOWN | Secondary Control Channel (No traffic observed) | `0.00` | GATT discovery table entry; zero traffic in captures. |
| `00002a26-0000-1000-8000-00805f9b34fb` | `20` | `0000180a-0000-1000-8000-00805f9b34fb` | `READ` | ASCII String | Firmware Revision String | `0.90` | GATT discovery on Device Information Service. |
| `00002a28-0000-1000-8000-00805f9b34fb` | In `89`–`105` | `0000180a-0000-1000-8000-00805f9b34fb` | `READ` | ASCII String | Software Revision String | `0.90` | GATT discovery on Device Information Service. |
| `00002a29-0000-1000-8000-00805f9b34fb` | In `89`–`105` | `0000180a-0000-1000-8000-00805f9b34fb` | `READ` | ASCII String | Manufacturer Name String | `0.90` | GATT discovery on Device Information Service. |
| `00002a19-0000-1000-8000-00805f9b34fb` | `10` | `0000180f-0000-1000-8000-00805f9b34fb` | `READ`, `NOTIFY` | 1-byte uint8 (0–100%) | Battery Level State-of-Charge Percentage | `0.95` | Standard Bluetooth SIG UUID + 0–100 percentage range heuristic. |
| `00002a00-0000-1000-8000-00805f9b34fb` | `3` | `00001800-0000-1000-8000-00805f9b34fb` | `READ` | UTF-8 String | Device Advertised Name | `1.00` | Standard GAP advertizing and GATT read PDU. |
| `00002a01-0000-1000-8000-00805f9b34fb` | `5` | `00001800-0000-1000-8000-00805f9b34fb` | `READ` | 2-byte uint16 | Device Appearance Category | `1.00` | Standard GAP discovery. |
| `00002a05-0000-1000-8000-00805f9b34fb` | `11` | `00001801-0000-1000-8000-00805f9b34fb` | `INDICATE` | 4-byte handle range | GATT Service Changed Indication | `1.00` | Standard GATT service change indication. |
| `00002902-0000-1000-8000-00805f9b34fb` | `83` / `12` | Descriptor | `READ`, `WRITE` | 2-byte uint16 bitfield | Client Characteristic Configuration Descriptor (CCCD) | `0.85` | Standard CCCD write request (`0x0100` enable notifications). |
| `HEURISTIC_TEMP_CHAN` | Diff Handle | Telemetry Service | `NOTIFY` | 2-byte int16 (signed °C) | Temperature Telemetry Channel (-20 to +80 °C) | `0.40`–`0.95` | Value diff correlation in plausible Celsius range. |
| `HEURISTIC_VOLT_CHAN` | Diff Handle | Telemetry Service | `NOTIFY` | 2-byte uint16 (mV / cV) | Battery Pack Voltage Telemetry Channel (2500–5000 mV) | `0.30`–`0.35` | Value diff correlation in plausible voltage range. |
| `HEURISTIC_GPS_CHAN` | Diff Handle | Telemetry Service | `NOTIFY` | 4-byte float32 (deg) | GPS Coordinate Telemetry Channel (-180.0 to +180.0) | `0.30` | Value diff correlation in geographic coordinate float range. |
| `HEURISTIC_MODE_CHAN` | Diff Handle | Telemetry Service | `NOTIFY` | 1-byte uint8 (enum) | Ride / Drive Mode Channel (1=Eco, 2=Normal, 3=Sport) | `0.45` | Value diff correlation with small discrete enum values. |
| `HEURISTIC_CHG_CHAN` | Diff Handle | Telemetry Service | `NOTIFY` | 1-byte uint8 (boolean) | Charging State Channel (`0x00`=Discharging, `0x01`=Charging) | `0.55` | Value diff correlation with single boolean-like byte. |

---

## Detailed Characteristic Specifications

### 1. `49535343-1e4d-4bd9-ba61-23c647249616` — Primary Vehicle Control & Telemetry

| Parameter | Specification |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Declaration Handle** | `81` |
| **Value Handle** | `82` |
| **Properties** | `WRITE` (`0x08`), `NOTIFY` (`0x10`) |
| **Associated Descriptors** | CCCD Handle `83` (`00002902-0000-1000-8000-00805f9b34fb`) |
| **Data Format** | Mixed ASCII string commands / structured telemetry frames |
| **Confidence** | `0.90` (Direct Hardware Confirmation) |
| **Evidence** | Directly observed in `commands.csv` and `notifications.csv` from analyzed RV400 capture. Re-verified twice independently in Module 10 live client. |
| **Capture Reference** | Value Handle `82` (Service Handles `80`–`88`) |

#### Supported Operations & Payloads
- **Pairing Authentication Write**: `PAIR<token>#` (`WRITE_REQUEST` / `WRITE_COMMAND`)
- **Pairing Response**: `ACCEPTED` (`HANDLE_VALUE_NOTIFICATION`)
- **Ignition ON Write**: `VS,ON` (`WRITE_REQUEST` / `WRITE_COMMAND`)
- **Ignition OFF Write**: `VS,OFF` (`WRITE_REQUEST` / `WRITE_COMMAND`)
- **Telemetry Frame**: `LD,...` (`HANDLE_VALUE_NOTIFICATION`)
- **Heartbeat Beacon**: Periodic 1–4 byte payloads (`HANDLE_VALUE_NOTIFICATION`)

---

### 2. Handle 85 Characteristic (Unobserved Write)

| Parameter | Specification |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Value Handle** | `85` |
| **Properties** | `WRITE` (`0x08`) |
| **Data Format** | UNKNOWN |
| **Confidence** | `0.00` (Unobserved) |
| **Evidence** | Structurally allocated in GATT table for Service `49535343-fe7d-4ae5-8fa9-9fafd205e455`; zero ATT transactions recorded in captures. |
| **Capture Reference** | Value Handle `85` |

---

### 3. Handle 87 Characteristic (Unobserved Write+Notify)

| Parameter | Specification |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Value Handle** | `87` |
| **Properties** | `WRITE` (`0x08`), `NOTIFY` (`0x10`) |
| **Data Format** | UNKNOWN |
| **Confidence** | `0.00` (Unobserved) |
| **Evidence** | Structurally allocated in GATT table for Service `49535343-fe7d-4ae5-8fa9-9fafd205e455`; zero ATT transactions recorded in captures. |
| **Capture Reference** | Value Handle `87` |

---

### 4. `00002a26-0000-1000-8000-00805f9b34fb` — Firmware Revision String

| Parameter | Specification |
|---|---|
| **Service UUID** | `0000180a-0000-1000-8000-00805f9b34fb` |
| **Value Handle** | `20` (or handle within `89`–`105` range) |
| **Properties** | `READ` (`0x02`) |
| **Data Format** | ASCII string (e.g. `1.2.3`) |
| **Confidence** | `0.90` (Bluetooth SIG Standard Specification) |
| **Evidence** | Standard GATT discovery output on Device Information Service. |
| **Capture Reference** | Device Information Service Handle |

---

### 5. `00002a19-0000-1000-8000-00805f9b34fb` — Battery Level Percentage

| Parameter | Specification |
|---|---|
| **Service UUID** | `0000180f-0000-1000-8000-00805f9b34fb` |
| **Value Handle** | `10` |
| **Properties** | `READ` (`0x02`), `NOTIFY` (`0x10`) |
| **Data Format** | 1-byte uint8 (`0x00`–`0x64` representing 0–100%) |
| **Confidence** | `0.95` (Bluetooth SIG Standard UUID `2a19` + range heuristic) |
| **Evidence** | Observed notification carrying single byte battery percentage. |
| **Capture Reference** | Value Handle `10` |

---

### 6. `00002902-0000-1000-8000-00805f9b34fb` — Client Characteristic Configuration Descriptor (CCCD)

| Parameter | Specification |
|---|---|
| **Parent Characteristic** | Characteristics with `NOTIFY` or `INDICATION` properties (e.g., Handle `82`) |
| **Descriptor Handle** | `83` (for Handle `82`) / `12` |
| **Properties** | `READ` (`0x02`), `WRITE` (`0x08`) |
| **Data Format** | 2-byte little-endian uint16 bitfield:<br>• `0x0000`: Notifications/Indications Disabled<br>• `0x0100`: Notifications Enabled<br>• `0x0200`: Indications Enabled |
| **Confidence** | `0.85` (Bluetooth SIG Standard Descriptor `2902`) |
| **Evidence** | Directly observed in CCCD write requests during BLE client initialization. |
| **Capture Reference** | Descriptor Handle `83` |

---
*Generated using `revolt_ble_toolkit` empirical protocol analysis pipeline.*
