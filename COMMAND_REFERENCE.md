# COMMAND_REFERENCE.md

## Revolt RV400 BLE Command Reference

This document details every observable command, notification, and control PDU discovered within the Revolt RV400 BLE vehicle-control protocol. 

Each entry strictly includes all mandatory fields:
- **Service UUID**
- **Characteristic UUID**
- **Opcode**
- **Payload**
- **Response**
- **Confidence**
- **Evidence**
- **Capture Reference**

---

## Command Catalog Index

1. [`CMD_PAIR_AUTH`](#1-cmd_pair_auth---pairing-authentication-handshake) — Vehicle Pairing Authentication Handshake
2. [`CMD_VEHICLE_ON`](#2-cmd_vehicle_on---vehicle-power-ignition-on) — Vehicle Power / Ignition ON
3. [`CMD_VEHICLE_OFF`](#3-cmd_vehicle_off---vehicle-power-ignition-off) — Vehicle Power / Ignition OFF
4. [`NTF_PAIR_ACCEPTED`](#4-ntf_pair_accepted---pairing-accepted-notification) — Pairing Accepted Notification
5. [`NTF_TELEMETRY_STREAM`](#5-ntf_telemetry_stream---live-vehicle-telemetry-stream) — Live Vehicle Telemetry Stream (`LD,...`)
6. [`NTF_HEARTBEAT`](#6-ntf_heartbeat---periodic-keep-alive-heartbeat) — Periodic Keep-Alive Heartbeat
7. [`CMD_CCCD_ENABLE_NOTIFY`](#7-cmd_cccd_enable_notify---enable-cccd-notifications) — Enable CCCD Notifications
8. [`CMD_EXCHANGE_MTU`](#8-cmd_exchange_mtu---att-exchange-mtu-requestresponse) — ATT Exchange MTU Request & Response
9. [`CMD_READ_FIRMWARE_REV`](#9-cmd_read_firmware_rev---read-firmware-revision) — Read Firmware Revision String
10. [`CMD_READ_SOFTWARE_REV`](#10-cmd_read_software_rev---read-software-revision) — Read Software Revision String
11. [`CMD_READ_MANUFACTURER_NAME`](#11-cmd_read_manufacturer_name---read-manufacturer-name) — Read Manufacturer Name
12. [`NTF_BATTERY_LEVEL`](#12-ntf_battery_level---battery-level-notification) — Battery Level Notification
13. [`NTF_TEMPERATURE`](#13-ntf_temperature---temperature-telemetry-notification) — Temperature Telemetry Notification
14. [`NTF_VOLTAGE`](#14-ntf_voltage---battery-pack-voltage-notification) — Battery Pack Voltage Notification
15. [`NTF_GPS_COORDINATE`](#15-ntf_gps_coordinate---gps-location-coordinate-notification) — GPS Location Coordinate Notification
16. [`NTF_RIDE_MODE`](#16-ntf_ride_mode---ride-drive-mode-notification) — Ride / Drive Mode Notification
17. [`NTF_CHARGING_STATE`](#17-ntf_charging_state---battery-charging-state-notification) — Battery Charging State Notification
18. [`CMD_GENERIC_CONTROL_WRITE`](#18-cmd_generic_control_write---generic-control-write) — Generic Control Write Command
19. [`CHAR_UNOBSERVED_85`](#19-char_unobserved_85---unobserved-write-characteristic) — Unobserved Write Characteristic (Handle 85)
20. [`CHAR_UNOBSERVED_87`](#20-char_unobserved_87---unobserved-writenotify-characteristic) — Unobserved Write+Notify Characteristic (Handle 87)

---

### 1. `CMD_PAIR_AUTH` - Pairing Authentication Handshake

| Field | Detail |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Characteristic UUID** | `49535343-1e4d-4bd9-ba61-23c647249616` |
| **Opcode** | `0x12` (`ATT_WRITE_REQ`) / `0x52` (`ATT_WRITE_CMD`) |
| **Payload** | ASCII string `PAIR<token>#`<br>Hex example (`PAIR<TOKEN>#`): `50 41 49 52 3c 54 4f 4b 45 4e 3e 23` |
| **Response** | Asynchronous notification `NTF_PAIR_ACCEPTED` (`ACCEPTED` / hex `41 43 43 45 50 54 45 44`) on same characteristic |
| **Confidence** | `0.90` (Direct Hardware Confirmation) |
| **Evidence** | Directly observed carrying `PAIR...#` write requests and `ACCEPTED` notification responses in `commands.csv` / `notifications.csv` from analyzed RV400 BTSnoop capture. |
| **Capture Reference** | Value Handle `82` (GATT Service Handles `80`–`88`) |

**Description**: Initiates the session pairing sequence with the Revolt vehicle controller. The caller sends a custom authentication token formatted with a `PAIR` prefix and `#` terminator.

---

### 2. `CMD_VEHICLE_ON` - Vehicle Power / Ignition ON

| Field | Detail |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Characteristic UUID** | `49535343-1e4d-4bd9-ba61-23c647249616` |
| **Opcode** | `0x12` (`ATT_WRITE_REQ`) / `0x52` (`ATT_WRITE_CMD`) |
| **Payload** | ASCII string `VS,ON`<br>Hex: `56 53 2c 4f 4e` |
| **Response** | Vehicle telemetry status notification frame / ACK |
| **Confidence** | `0.85` (Observed Command Frame) |
| **Evidence** | Observed carrying literal `VS,ON` write payload in captured RV400 logs. |
| **Capture Reference** | Value Handle `82` |

**Description**: Commands the Revolt vehicle controller to enable ignition / high-voltage powertrain systems.

---

### 3. `CMD_VEHICLE_OFF` - Vehicle Power / Ignition OFF

| Field | Detail |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Characteristic UUID** | `49535343-1e4d-4bd9-ba61-23c647249616` |
| **Opcode** | `0x12` (`ATT_WRITE_REQ`) / `0x52` (`ATT_WRITE_CMD`) |
| **Payload** | ASCII string `VS,OFF`<br>Hex: `56 53 2c 4f 46 46` |
| **Response** | Vehicle telemetry status notification frame / ACK |
| **Confidence** | `0.85` (Observed Command Frame) |
| **Evidence** | Observed carrying literal `VS,OFF` write payload in captured RV400 logs. |
| **Capture Reference** | Value Handle `82` |

**Description**: Commands the vehicle controller to disable ignition / power down the vehicle.

---

### 4. `NTF_PAIR_ACCEPTED` - Pairing Accepted Notification

| Field | Detail |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Characteristic UUID** | `49535343-1e4d-4bd9-ba61-23c647249616` |
| **Opcode** | `0x1b` (`ATT_HANDLE_VALUE_NTF`) |
| **Payload** | ASCII string `ACCEPTED`<br>Hex: `41 43 43 45 50 54 45 44` |
| **Response** | None (Server-initiated notification push) |
| **Confidence** | `0.90` (Direct Hardware Confirmation) |
| **Evidence** | Received immediately following valid `PAIR<token>#` write request in live client and capture logs. |
| **Capture Reference** | Value Handle `82` |

**Description**: Sent by the vehicle MCU to acknowledge successful token validation and unlock operational command privileges.

---

### 5. `NTF_TELEMETRY_STREAM` - Live Vehicle Telemetry Stream (`LD,...`)

| Field | Detail |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Characteristic UUID** | `49535343-1e4d-4bd9-ba61-23c647249616` |
| **Opcode** | `0x1b` (`ATT_HANDLE_VALUE_NTF`) |
| **Payload** | ASCII comma-separated telemetry frame prefixed with `LD,...` (containing device parameters, coordinates, timestamps) |
| **Response** | None (Server-initiated notification push) |
| **Confidence** | `0.90` (Direct Hardware Confirmation) |
| **Evidence** | Directly observed `LD,...` structured telemetry notification frames on handle `82` in RV400 captures. |
| **Capture Reference** | Value Handle `82` |

**Description**: Periodic or event-driven telemetry stream containing vehicle diagnostic data.

---

### 6. `NTF_HEARTBEAT` - Periodic Keep-Alive Heartbeat

| Field | Detail |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Characteristic UUID** | `49535343-1e4d-4bd9-ba61-23c647249616` |
| **Opcode** | `0x1b` (`ATT_HANDLE_VALUE_NTF`) |
| **Payload** | Small byte sequence (1–4 bytes, e.g. `0x01` or `0x0102`) |
| **Response** | None (Server-initiated notification push) |
| **Confidence** | `0.65` (Behavioral Heuristic: regular intervals cv < 0.3) |
| **Evidence** | Classified by `ProtocolAnalyzer` on channels emitting small regular notification intervals. |
| **Capture Reference** | Value Handle `82` |

**Description**: Low-overhead periodic beacon sent by vehicle MCU to maintain active BLE connection state.

---

### 7. `CMD_CCCD_ENABLE_NOTIFY` - Enable CCCD Notifications

| Field | Detail |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Characteristic UUID** | `00002902-0000-1000-8000-00805f9b34fb` (Descriptor UUID) |
| **Opcode** | `0x12` (`ATT_WRITE_REQ`) |
| **Payload** | 2-byte little-endian uint16: `0x0100` (Enable Notifications) / `0x0000` (Disable) |
| **Response** | `0x13` (`ATT_WRITE_RSP`) |
| **Confidence** | `0.85` (Known Configuration UUID `2902`) |
| **Evidence** | Standard CCCD configuration write observed during BLE subscription sequence. |
| **Capture Reference** | Descriptor Handle `83` / `12` |

**Description**: Configures Client Characteristic Configuration Descriptor (CCCD) to subscribe to notifications on control/telemetry characteristics.

---

### 8. `CMD_EXCHANGE_MTU` - ATT Exchange MTU Request/Response

| Field | Detail |
|---|---|
| **Service UUID** | N/A (Link Protocol) |
| **Characteristic UUID** | N/A (Link Protocol) |
| **Opcode** | `0x02` (`ATT_EXCHANGE_MTU_REQ`) / `0x03` (`ATT_EXCHANGE_MTU_RSP`) |
| **Payload** | 2-byte little-endian uint16 Rx MTU (e.g. `0xf700` = 247 bytes) |
| **Response** | 2-byte little-endian uint16 Server Rx MTU |
| **Confidence** | `0.80` (Standard ATT Negotiation PDU) |
| **Evidence** | Observed in BTSnoop HCI parsing layer. |
| **Capture Reference** | Connection Handle `1` (No attribute handle) |

**Description**: Negotiates maximum ATT PDU payload size between host and vehicle BLE controller.

---

### 9. `CMD_READ_FIRMWARE_REV` - Read Firmware Revision String

| Field | Detail |
|---|---|
| **Service UUID** | `0000180a-0000-1000-8000-00805f9b34fb` |
| **Characteristic UUID** | `00002a26-0000-1000-8000-00805f9b34fb` |
| **Opcode** | `0x0a` (`ATT_READ_REQ`) / `0x0b` (`ATT_READ_RSP`) |
| **Payload** | Request: Empty payload<br>Response: ASCII string (e.g., `1.2.3`) |
| **Response** | `0x0b` (`ATT_READ_RSP`) carrying firmware version string |
| **Confidence** | `0.90` (Bluetooth SIG standard UUID `2a26`) |
| **Evidence** | GATT discovery output on Device Information Service (handles `89`–`105`). |
| **Capture Reference** | Value Handle `20` / Handle within `89`–`105` |

**Description**: Reads vehicle MCU firmware revision string.

---

### 10. `CMD_READ_SOFTWARE_REV` - Read Software Revision String

| Field | Detail |
|---|---|
| **Service UUID** | `0000180a-0000-1000-8000-00805f9b34fb` |
| **Characteristic UUID** | `00002a28-0000-1000-8000-00805f9b34fb` |
| **Opcode** | `0x0a` (`ATT_READ_REQ`) / `0x0b` (`ATT_READ_RSP`) |
| **Payload** | Request: Empty payload<br>Response: ASCII string |
| **Response** | `0x0b` (`ATT_READ_RSP`) carrying software version string |
| **Confidence** | `0.90` (Bluetooth SIG standard UUID `2a28`) |
| **Evidence** | GATT discovery output on Device Information Service. |
| **Capture Reference** | Device Information Service Handle |

**Description**: Reads vehicle software application revision string.

---

### 11. `CMD_READ_MANUFACTURER_NAME` - Read Manufacturer Name

| Field | Detail |
|---|---|
| **Service UUID** | `0000180a-0000-1000-8000-00805f9b34fb` |
| **Characteristic UUID** | `00002a29-0000-1000-8000-00805f9b34fb` |
| **Opcode** | `0x0a` (`ATT_READ_REQ`) / `0x0b` (`ATT_READ_RSP`) |
| **Payload** | Request: Empty payload<br>Response: ASCII string |
| **Response** | `0x0b` (`ATT_READ_RSP`) carrying manufacturer string |
| **Confidence** | `0.90` (Bluetooth SIG standard UUID `2a29`) |
| **Evidence** | GATT discovery output on Device Information Service. |
| **Capture Reference** | Device Information Service Handle |

**Description**: Reads vehicle manufacturer string.

---

### 12. `NTF_BATTERY_LEVEL` - Battery Level Notification

| Field | Detail |
|---|---|
| **Service UUID** | `0000180f-0000-1000-8000-00805f9b34fb` |
| **Characteristic UUID** | `00002a19-0000-1000-8000-00805f9b34fb` |
| **Opcode** | `0x1b` (`ATT_HANDLE_VALUE_NTF`) / `0x0b` (`ATT_READ_RSP`) |
| **Payload** | 1-byte uint8 percentage (`0x00`–`0x64` representing 0–100%) |
| **Response** | None (Notification PDU) |
| **Confidence** | `0.95` (Known Battery Level UUID `2a19` + 0–100 range heuristic) |
| **Evidence** | Single byte in 0–100 range observed on battery service handle. |
| **Capture Reference** | Value Handle `10` |

**Description**: Transmits current battery charge level percentage.

---

### 13. `NTF_TEMPERATURE` - Temperature Telemetry Notification

| Field | Detail |
|---|---|
| **Service UUID** | Standard / Custom Telemetry Service |
| **Characteristic UUID** | `00002a1c-0000-1000-8000-00805f9b34fb` / `00002a6e-0000-1000-8000-00805f9b34fb` / Custom |
| **Opcode** | `0x1b` (`ATT_HANDLE_VALUE_NTF`) |
| **Payload** | 2-byte signed integer `int16` (little-endian, range -20 to +80 °C) |
| **Response** | None |
| **Confidence** | `0.40`–`0.95` (Heuristic range correlation) |
| **Evidence** | Change correlation in plausible Celsius temperature range. |
| **Capture Reference** | Attribute Handle Diff |

**Description**: Reports motor or battery thermal telemetry.

---

### 14. `NTF_VOLTAGE` - Battery Pack Voltage Notification

| Field | Detail |
|---|---|
| **Service UUID** | UNKNOWN |
| **Characteristic UUID** | UNKNOWN |
| **Opcode** | `0x1b` (`ATT_HANDLE_VALUE_NTF`) |
| **Payload** | 2-byte unsigned integer `uint16` (little-endian, 2500–5000 mV or 250–500 cV) |
| **Response** | None |
| **Confidence** | `0.30`–`0.35` (Heuristic millivolt/centivolt range) |
| **Evidence** | 2-byte unsigned value in plausible voltage range. |
| **Capture Reference** | Attribute Handle Diff |

**Description**: Reports pack/cell voltage readings.

---

### 15. `NTF_GPS_COORDINATE` - GPS Location Coordinate Notification

| Field | Detail |
|---|---|
| **Service UUID** | UNKNOWN |
| **Characteristic UUID** | UNKNOWN |
| **Opcode** | `0x1b` (`ATT_HANDLE_VALUE_NTF`) |
| **Payload** | 4-byte IEEE 754 floating point number `float32` (little-endian, -180.0 to +180.0) |
| **Response** | None |
| **Confidence** | `0.30` (Heuristic float32 range correlation) |
| **Evidence** | 4-byte float values observed in capture notifications. |
| **Capture Reference** | Attribute Handle Diff |

**Description**: Reports vehicle geographic latitude/longitude coordinate.

---

### 16. `NTF_RIDE_MODE` - Ride / Drive Mode Notification

| Field | Detail |
|---|---|
| **Service UUID** | UNKNOWN |
| **Characteristic UUID** | UNKNOWN |
| **Opcode** | `0x1b` (`ATT_HANDLE_VALUE_NTF`) |
| **Payload** | 1-byte uint8 enum (1=Eco, 2=Normal, 3=Sport) |
| **Response** | None |
| **Confidence** | `0.45` (Single byte discrete enum heuristic) |
| **Evidence** | Small discrete byte values observed in capture notifications. |
| **Capture Reference** | Attribute Handle Diff |

**Description**: Reports active vehicle performance profile / ride mode.

---

### 17. `NTF_CHARGING_STATE` - Battery Charging State Notification

| Field | Detail |
|---|---|
| **Service UUID** | UNKNOWN |
| **Characteristic UUID** | UNKNOWN |
| **Opcode** | `0x1b` (`ATT_HANDLE_VALUE_NTF`) |
| **Payload** | 1-byte boolean byte (`0x00` = Discharging, `0x01` = Charging) |
| **Response** | None |
| **Confidence** | `0.55` (Single boolean-like byte heuristic) |
| **Evidence** | Boolean state transition observed between captures. |
| **Capture Reference** | Attribute Handle Diff |

**Description**: Indicates whether vehicle charger is connected and actively charging.

---

### 18. `CMD_GENERIC_CONTROL_WRITE` - Generic Control Write

| Field | Detail |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Characteristic UUID** | `49535343-1e4d-4bd9-ba61-23c647249616` |
| **Opcode** | `0x12` (`ATT_WRITE_REQ`) / `0x52` (`ATT_WRITE_CMD`) |
| **Payload** | Binary or ASCII command string (e.g. `0x0102`) |
| **Response** | Variable / None |
| **Confidence** | `0.40` (Generic write classification) |
| **Evidence** | ATT Write PDU targeted at control characteristic value handle `82`. |
| **Capture Reference** | Value Handle `82` |

**Description**: Generic fallback write command targeting vehicle control characteristic.

---

### 19. `CHAR_UNOBSERVED_85` - Unobserved Write Characteristic (Handle 85)

| Field | Detail |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Characteristic UUID** | UNKNOWN |
| **Opcode** | `0x12` (`ATT_WRITE_REQ`) / `0x52` (`ATT_WRITE_CMD`) |
| **Payload** | UNKNOWN |
| **Response** | UNKNOWN |
| **Confidence** | `0.00` (Unobserved) |
| **Evidence** | Structurally present at handle `85` in GATT attribute table; zero traffic recorded in captured logs. |
| **Capture Reference** | Value Handle `85` |

**Description**: Write-only characteristic allocated in ISSC service table whose specific command purpose is unobserved.

---

### 20. `CHAR_UNOBSERVED_87` - Unobserved Write+Notify Characteristic (Handle 87)

| Field | Detail |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Characteristic UUID** | UNKNOWN |
| **Opcode** | `0x12` / `0x1b` |
| **Payload** | UNKNOWN |
| **Response** | UNKNOWN |
| **Confidence** | `0.00` (Unobserved) |
| **Evidence** | Structurally present at handle `87` in GATT attribute table; zero traffic recorded in captured logs. |
| **Capture Reference** | Value Handle `87` |

**Description**: Secondary write+notify characteristic allocated in ISSC service table whose specific command purpose is unobserved.

---
*Generated using `revolt_ble_toolkit` empirical protocol analysis pipeline.*
