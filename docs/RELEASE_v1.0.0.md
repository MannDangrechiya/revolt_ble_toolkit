# revolt_ble_toolkit v1.0.0 — Release Notes

**Release Version:** `v1.0.0`  
**Release Date:** August 4, 2026  
**Status:** **Production Candidate (v1.0.0)**  

---

## 1. Highlights

First Production Candidate release of `revolt_ble_toolkit` (v1.0.0) — a professional Python 3.12 toolkit for reverse-engineering Bluetooth Low Energy traffic captured in Android HCI Snoop Logs.

---

## 2. Included Modules

- **BTSnoop HCI Parser**: Decodes Android `btsnoop_hci.log` into structured ACL connection events.
- **ATT PDU Parser**: Decodes GATT Read/Write requests, responses, and notification PDUs.
- **GATT Hierarchy Analyzer**: Reconstructs services, characteristics, and descriptors tables.
- **Protocol Classifier**: Heuristic classifier providing confidence-scored ATT payload classifications.
- **Capture Comparator**: Diff engine comparing two capture logs by GATT attribute handles.
- **Desktop PySide6 GUI**: Offscreen-tested Qt GUI (`revolt-ble-gui`) with packet table filtering and timeline seek.
- **Live BLE Client**: Bleak-backed live client (`revolt-ble-live`) for real-time device interaction.

---

## 3. Validation Status

- **Pytest Suite**: Passed (170/170 tests, 92% coverage).
- **Physical Hardware Verification**: **`Pending Real Hardware Validation`**.
