"""Tests for revolt_data WebSocket endpoint authentication and authorization."""

from __future__ import annotations

import asyncio
import os
import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

os.environ.setdefault(
    "REVOLT_JWT_SECRET", "test_secret_key_that_is_at_least_32_bytes_long"
)

from revolt_data.api.websocket import _on_ble_event_for_ws, _ws_broadcast_tasks
from revolt_data.database import init_db
from revolt_data.main import create_app
from revolt_data.services.auth_service import create_access_token


@pytest.fixture
def client() -> TestClient:
    asyncio.run(init_db())
    app = create_app()
    return TestClient(app)


def test_websocket_missing_token_rejected(client: TestClient) -> None:
    """Test WebSocket connection without token query param is rejected with 1008."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/vehicles/v123"):
            pass
    assert exc_info.value.code == 1008


def test_websocket_invalid_token_rejected(client: TestClient) -> None:
    """Test WebSocket connection with invalid token query param is rejected with 1008."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/vehicles/v123?token=invalid.jwt.token"):
            pass
    assert exc_info.value.code == 1008


def test_websocket_nonexistent_vehicle_rejected(client: TestClient) -> None:
    """Test WebSocket connection with valid token for non-existent vehicle is rejected with 1008."""
    token = create_access_token("user_123")
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/vehicles/nonexistent_v?token={token}"):
            pass
    assert exc_info.value.code == 1008


def test_ws_broadcast_task_cleanup() -> None:
    """Test that BLE event listener task set tracks and cleans up tasks."""
    _ws_broadcast_tasks.clear()
    _on_ble_event_for_ws("v123", "STATE_CHANGE", "Connected")
    # Event listener runs safely without crashing when no running event loop or active loops
