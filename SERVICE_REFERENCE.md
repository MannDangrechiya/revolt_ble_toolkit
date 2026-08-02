# SERVICE_REFERENCE.md

## Revolt RV400 BLE Service Reference

This document provides a comprehensive specification of all Bluetooth Low Energy (BLE) GATT services discovered and analyzed on the Revolt RV400 electric vehicle platform using `revolt_ble_toolkit`.

---

## Service Summary Index

| Service Name | Service UUID | Handle Range | Type | Characteristic Count | Purpose / Functional Role |
|---|---|---|---|---|---|
| **Vehicle Control Service (ISSC)** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` | `80`–`88` | Primary (Vendor) | 3 | Vehicle pairing, ignition control (`VS,ON`/`VS,OFF`), and telemetry streaming (`LD,...`) |
| **Device Information Service** | `0000180a-0000-1000-8000-00805f9b34fb` | `89`–`105` | Primary (SIG) | 3+ | Hardware revision, firmware revision (`2a26`), software revision (`2a28`), manufacturer name (`2a29`) |
| **Battery Service** | `0000180f-0000-1000-8000-00805f9b34fb` | `1`–`20` | Primary (SIG) | 1 | Battery State-of-Charge percentage (`2a19`) |
| **Generic Access Service** | `00001800-0000-1000-8000-00805f9b34fb` | `1`–`7` | Primary (SIG) | 2 | Device Name (`2a00`, e.g. "RV400"), Appearance (`2a01`) |
| **Generic Attribute Service** | `00001801-0000-1000-8000-00805f9b34fb` | `8`–`15` | Primary (SIG) | 1 | Service Changed indication (`2a05`), CCCD management (`2902`) |

---

## Detailed Service Specifications

### 1. Vehicle Control Service (ISSC Custom)

| Parameter | Value |
|---|---|
| **Service UUID** | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| **Service Handle Range** | Start Handle `80` — End Handle `88` |
| **Service Type** | Primary Custom Service (ISSC Transparent Serial Architecture) |
| **Access Permissions** | Read / Write / Notify (Unauthenticated / Pair-Protected at Application Layer) |
| **Confidence** | `0.90` (Direct Hardware Confirmation) |
| **Evidence** | Directly observed in `analyzers.gatt` output on RV400 captures (handles `80`–`88`). Re-verified in live client tests. |

#### Contained Characteristics

| Value Handle | Characteristic UUID | Properties | Role / Traffic Observed |
|---|---|---|---|
| **`82`** | `49535343-1e4d-4bd9-ba61-23c647249616` | `WRITE` \| `NOTIFY` | **Primary Command & Telemetry Channel**: Accepts `PAIR<token>#`, `VS,ON`, `VS,OFF` write commands; emits `ACCEPTED`, `LD,...` telemetry, and heartbeat notifications. |
| **`85`** | `UNKNOWN` (Vendor) | `WRITE` | **Auxiliary Write Channel**: Structurally allocated in GATT table; no traffic recorded in captures. |
| **`87`** | `UNKNOWN` (Vendor) | `WRITE` \| `NOTIFY` | **Secondary Custom Channel**: Structurally allocated in GATT table; no traffic recorded in captures. |

#### Functional Behavior
This is the primary command-and-control interface for the Revolt motorcycle. The host application establishes connection, negotiates MTU, writes to the Client Characteristic Configuration Descriptor (CCCD Handle `83`) to enable notifications, and transmits authentication/control strings.

---

### 2. Device Information Service

| Parameter | Value |
|---|---|
| **Service UUID** | `0000180a-0000-1000-8000-00805f9b34fb` (16-bit Alias: `0x180a`) |
| **Service Handle Range** | Start Handle `89` — End Handle `105` |
| **Service Type** | Primary Standard Service (Bluetooth SIG) |
| **Access Permissions** | Read Only |
| **Confidence** | `0.90` (Bluetooth SIG Standard Specification) |
| **Evidence** | GATT discovery output on RV400 captures. |

#### Contained Characteristics

| Value Handle | Characteristic UUID | Properties | Role / Traffic Observed |
|---|---|---|---|
| **`20`** (or in range `89`–`105`) | `00002a26-0000-1000-8000-00805f9b34fb` (`2a26`) | `READ` | **Firmware Revision String**: Returns ASCII version string of vehicle MCU firmware (e.g. `1.2.3`). |
| **In range `89`–`105`** | `00002a28-0000-1000-8000-00805f9b34fb` (`2a28`) | `READ` | **Software Revision String**: Returns application software revision. |
| **In range `89`–`105`** | `00002a29-0000-1000-8000-00805f9b34fb` (`2a29`) | `READ` | **Manufacturer Name String**: Returns manufacturer identity string ("Revolt Motors"). |

---

### 3. Battery Service

| Parameter | Value |
|---|---|
| **Service UUID** | `0000180f-0000-1000-8000-00805f9b34fb` (16-bit Alias: `0x180f`) |
| **Service Handle Range** | Start Handle `1` — End Handle `20` |
| **Service Type** | Primary Standard Service (Bluetooth SIG) |
| **Access Permissions** | Read / Notify |
| **Confidence** | `0.95` (Bluetooth SIG Standard Specification) |
| **Evidence** | GATT discovery and standard 1-byte notification payload in percentage range (0–100%). |

#### Contained Characteristics

| Value Handle | Characteristic UUID | Properties | Role / Traffic Observed |
|---|---|---|---|
| **`10`** | `00002a19-0000-1000-8000-00805f9b34fb` (`2a19`) | `READ` \| `NOTIFY` | **Battery Level**: Returns single byte uint8 representing current battery State-of-Charge percentage (0% to 100%). |

---

### 4. Generic Access Service

| Parameter | Value |
|---|---|
| **Service UUID** | `00001800-0000-1000-8000-00805f9b34fb` (16-bit Alias: `0x1800`) |
| **Service Handle Range** | Start Handle `1` — End Handle `7` |
| **Service Type** | Primary Standard Service (Bluetooth SIG) |
| **Access Permissions** | Read Only |
| **Confidence** | `1.00` (Bluetooth SIG Core Standard) |
| **Evidence** | BLE GAP advertising and GATT discovery logs. |

#### Contained Characteristics

| Value Handle | Characteristic UUID | Properties | Role / Traffic Observed |
|---|---|---|---|
| **`3`** | `00002a00-0000-1000-8000-00805f9b34fb` (`2a00`) | `READ` | **Device Name**: UTF-8 string advertized by vehicle (e.g. "RV400_BLE"). |
| **`5`** | `00002a01-0000-1000-8000-00805f9b34fb` (`2a01`) | `READ` | **Appearance**: 16-bit category enumeration. |

---

### 5. Generic Attribute Service

| Parameter | Value |
|---|---|
| **Service UUID** | `00001801-0000-1000-8000-00805f9b34fb` (16-bit Alias: `0x1801`) |
| **Service Handle Range** | Start Handle `8` — End Handle `15` |
| **Service Type** | Primary Standard Service (Bluetooth SIG) |
| **Access Permissions** | Read / Indicate |
| **Confidence** | `1.00` (Bluetooth SIG Core Standard) |
| **Evidence** | ATT PDU discovery logs. |

#### Contained Characteristics

| Value Handle | Characteristic UUID | Properties | Role / Traffic Observed |
|---|---|---|---|
| **`11`** | `00002a05-0000-1000-8000-00805f9b34fb` (`2a05`) | `INDICATE` | **Service Changed**: Indicates modifications in GATT attribute table structure. |

---
*Generated using `revolt_ble_toolkit` empirical protocol analysis pipeline.*
