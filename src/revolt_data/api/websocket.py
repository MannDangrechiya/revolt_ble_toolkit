"""FastAPI WebSocket Router for real-time live telemetry streaming."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_data.database import AsyncSessionLocal
from revolt_data.models.user import User
from revolt_data.models.vehicle import Vehicle
from revolt_data.services.auth_service import decode_access_token
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


_ws_broadcast_tasks: set[asyncio.Task[None]] = set()


def _on_ble_event_for_ws(vehicle_id: str, event_type: str, data: Any) -> None:
    payload = {
        "vehicle_id": vehicle_id,
        "event_type": event_type,
        "payload_type": type(data).__name__,
        "data": str(data),
    }
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    if loop.is_running():
        task = loop.create_task(ws_manager.broadcast(vehicle_id, payload))
        _ws_broadcast_tasks.add(task)
        task.add_done_callback(_ws_broadcast_tasks.discard)


# Register WS dispatcher with BLE manager
LiveBleManager.get_instance().add_event_listener(_on_ble_event_for_ws)


@router.websocket("/ws/vehicles/{vehicle_id}")
async def vehicle_telemetry_ws(
    websocket: WebSocket,
    vehicle_id: str,
    token: str | None = Query(None),
) -> None:
    """WebSocket endpoint streaming live BLE telemetry events for vehicle_id."""
    if not token:
        logger.warning("WebSocket connection rejected: Missing token for vehicle %s", vehicle_id)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = decode_access_token(token)
    if not user_id:
        logger.warning("WebSocket connection rejected: Invalid or expired token for vehicle %s", vehicle_id)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
            vehicle = result.scalar_one_or_none()

            if not vehicle:
                logger.warning("WebSocket connection rejected: Vehicle %s not found", vehicle_id)
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            if vehicle.owner_id != user_id:
                user_res = await session.execute(select(User).where(User.id == user_id))
                user = user_res.scalar_one_or_none()
                if not user or not user.is_superuser:
                    logger.warning(
                        "WebSocket connection rejected: User %s does not own vehicle %s",
                        user_id,
                        vehicle_id,
                    )
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
    except Exception:
        logger.exception("Error checking vehicle ownership for WebSocket")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect(vehicle_id, websocket)
    try:
        while True:
            # Keep socket alive and receive client ping/pong
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(vehicle_id, websocket)
