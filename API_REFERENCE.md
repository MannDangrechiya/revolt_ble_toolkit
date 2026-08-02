# API_REFERENCE.md

## `revolt_data` REST & WebSocket API Specification

This document provides the full technical reference for `revolt_data`'s HTTP REST endpoints and real-time WebSocket protocol streams.

---

## 1. Authentication & Headers

All protected REST API endpoints require a valid JSON Web Token (JWT) supplied in the HTTP `Authorization` header:

```http
Authorization: Bearer <access_token>
```

---

## 2. API Endpoint Index

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register` | Register a new user account | No |
| `POST` | `/auth/login` | Authenticate credentials & receive JWT token | No |
| `GET` | `/users/me` | Fetch authenticated user profile | Yes |
| `POST` | `/vehicles` | Register a new Revolt RV400 motorcycle | Yes |
| `GET` | `/vehicles` | List all vehicles owned by user | Yes |
| `GET` | `/vehicles/{vehicle_id}` | Fetch vehicle metadata & connection status | Yes |
| `POST` | `/vehicles/{vehicle_id}/connect` | Initiate live BLE connection via `revolt_ble_toolkit` | Yes |
| `GET` | `/vehicles/{vehicle_id}/trips` | Retrieve ride history trips | Yes |
| `GET` | `/vehicles/{vehicle_id}/telemetry` | Query decoded telemetry time-series records | Yes |
| `POST` | `/vehicles/{vehicle_id}/commands` | Dispatch async BLE command (`PAIR`, `VS_ON`, `VS_OFF`) | Yes |
| `WS` | `/ws/vehicles/{vehicle_id}` | Stream real-time telemetry events via WebSocket | Yes |

---

## 3. REST Endpoint Specifications

### 3.1 Authentication

#### `POST /auth/register`
Registers a new user account.

**Request Body** (`application/json`):
```json
{
  "email": "rider@revolt.com",
  "password": "SecurePassword123!",
  "full_name": "Revolt Rider"
}
```

**Response** (`201 Created`):
```json
{
  "id": "u_8f3a12b0-4c12-4f81-9b12-3456789abcde",
  "email": "rider@revolt.com",
  "full_name": "Revolt Rider",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2026-08-01T22:45:00Z"
}
```

---

#### `POST /auth/login`
Authenticates credentials and returns a JWT access token.

**Request Body** (`application/json`):
```json
{
  "email": "rider@revolt.com",
  "password": "SecurePassword123!"
}
```

**Response** (`200 OK`):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

### 3.2 Vehicles

#### `POST /vehicles`
Registers a new Revolt motorcycle.

**Request Body** (`application/json`):
```json
{
  "vin": "MB1RV400012345678",
  "name": "My RV400",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "pairing_token": "<TOKEN>"
}
```

**Response** (`201 Created`):
```json
{
  "id": "v_11223344-5566-7788-9900-aabbccddeeff",
  "owner_id": "u_8f3a12b0-4c12-4f81-9b12-3456789abcde",
  "vin": "MB1RV400012345678",
  "name": "My RV400",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "created_at": "2026-08-01T22:46:00Z",
  "status": {
    "connection_state": "DISCONNECTED",
    "is_authenticated": false,
    "ignition_on": false,
    "battery_percentage": 100,
    "last_seen": "2026-08-01T22:46:00Z"
  }
}
```

---

#### `POST /vehicles/{vehicle_id}/connect`
Initiates a background BLE connection to the vehicle using `revolt_ble_toolkit.live.RevoltLiveClient`.

**Response** (`200 OK`):
```json
{
  "vehicle_id": "v_11223344-5566-7788-9900-aabbccddeeff",
  "connection_state": "CONNECTING"
}
```

---

### 3.3 Commands

#### `POST /vehicles/{vehicle_id}/commands`
Dispatches a BLE command to the vehicle via `revolt_ble_toolkit`'s async write queue.

**Request Body** (`application/json`):
```json
{
  "command_type": "VS_ON",
  "token": null
}
```

**Response** (`200 OK`):
```json
{
  "command_id": "cmd_99887766-5544-3322-1100-ffeeddccbbaa",
  "vehicle_id": "v_11223344-5566-7788-9900-aabbccddeeff",
  "status": "EXECUTED",
  "message": "Command VS_ON dispatched successfully"
}
```

---

### 3.4 Telemetry

#### `GET /vehicles/{vehicle_id}/telemetry`
Retrieves decoded telemetry records.

**Query Parameters**:
- `limit` (integer, default `100`): Maximum number of records to return.

**Response** (`200 OK`):
```json
[
  {
    "id": "t_00112233-4455-6677-8899-aabbccddeeff",
    "vehicle_id": "v_11223344-5566-7788-9900-aabbccddeeff",
    "timestamp": "2026-08-01T22:47:00Z",
    "event_type": "BATTERY_STATUS",
    "battery_percentage": 85,
    "latitude": null,
    "longitude": null,
    "speed_kmh": null,
    "raw_payload": "Battery: 85%"
  }
]
```

---

## 4. WebSocket Event Stream

### `WS /ws/vehicles/{vehicle_id}`

Establishes a persistent, bi-directional WebSocket connection streaming live vehicle events emitted by `revolt_ble_toolkit`.

#### Broadcast Message Format (`JSON`)

**State Transition Event**:
```json
{
  "vehicle_id": "v_11223344-5566-7788-9900-aabbccddeeff",
  "event_type": "STATE_CHANGE",
  "payload_type": "ConnectionStateEvent",
  "data": "ConnectionStateEvent(previous_state=CONNECTING, new_state=CONNECTED, reason='Connected to AA:BB:CC:DD:EE:FF')"
}
```

**Decoded Telemetry Event**:
```json
{
  "vehicle_id": "v_11223344-5566-7788-9900-aabbccddeeff",
  "event_type": "DECODED_PAYLOAD",
  "payload_type": "DecodedTelemetryFrame",
  "data": "DecodedTelemetryFrame(timestamp=2026-08-01 22:47:00+00:00, raw_payload='LD,DEV123,12.34,56.78,1600000000', fields=['LD', 'DEV123', '12.34', '56.78', '1600000000'])"
}
```

---
*Generated for `revolt_data` FastAPI Backend Service.*
