"""FastAPI WebSocket Router for real-time live telemetry streaming."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_data.services.ble_manager import LiveBleManager

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


class WebSocketManager:
    """Manager for active WebSocket client connections."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, vehicle_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        conns = self.active_connections.setdefault(vehicle_id, [])
        conns.append(websocket)
        logger.info("WebSocket connected for vehicle %s", vehicle_id)

    def disconnect(self, vehicle_id: str, websocket: WebSocket) -> None:
        if vehicle_id in self.active_connections:
            conns = self.active_connections[vehicle_id]
            if websocket in conns:
                conns.remove(websocket)
                logger.info("WebSocket disconnected for vehicle %s", vehicle_id)

    async def broadcast(self, vehicle_id: str, payload: dict[str, Any]) -> None:
        if vehicle_id in self.active_connections:
            for websocket in list(self.active_connections[vehicle_id]):
                try:
                    await websocket.send_json(payload)
                except Exception:
                    self.disconnect(vehicle_id, websocket)


ws_manager = WebSocketManager()


_ws_broadcast_tasks: list[asyncio.Task[None]] = []


def _on_ble_event_for_ws(vehicle_id: str, event_type: str, data: Any) -> None:
    payload = {
        "vehicle_id": vehicle_id,
        "event_type": event_type,
        "payload_type": type(data).__name__,
        "data": str(data),
    }
    loop = asyncio.get_event_loop()
    if loop.is_running():
        task = loop.create_task(ws_manager.broadcast(vehicle_id, payload))
        _ws_broadcast_tasks.append(task)


# Register WS dispatcher with BLE manager
LiveBleManager.get_instance().add_event_listener(_on_ble_event_for_ws)


@router.websocket("/ws/vehicles/{vehicle_id}")
async def vehicle_telemetry_ws(websocket: WebSocket, vehicle_id: str) -> None:
    """WebSocket endpoint streaming live BLE telemetry events for vehicle_id."""
    await ws_manager.connect(vehicle_id, websocket)
    try:
        while True:
            # Keep socket alive and receive client ping/pong
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(vehicle_id, websocket)
