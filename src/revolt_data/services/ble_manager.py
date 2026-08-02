"""Live BLE Manager service using revolt_ble_toolkit.live.RevoltLiveClient."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.core.exceptions import LiveClientError
from revolt_ble_toolkit.live import CommandRequest, ConnectionState, RevoltLiveClient
from revolt_data.plugins.toolkit_plugin import RevoltDataBlePlugin

logger = get_logger(__name__)


class LiveBleManager:
    """Singleton manager controlling live BLE connections and revolt_ble_toolkit instances."""

    _instance: LiveBleManager | None = None

    def __init__(self) -> None:
        self._clients: dict[str, RevoltLiveClient] = {}
        self._plugins: dict[str, RevoltDataBlePlugin] = {}
        self._event_listeners: list[Callable[[str, str, Any], None]] = []

    @classmethod
    def get_instance(cls) -> LiveBleManager:
        if cls._instance is None:
            cls._instance = LiveBleManager()
        return cls._instance

    def add_event_listener(self, listener: Callable[[str, str, Any], None]) -> None:
        """Register a callback for all vehicle BLE events."""
        if listener not in self._event_listeners:
            self._event_listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[str, str, Any], None]) -> None:
        """Unregister an event listener callback."""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)

    def _on_plugin_event(self, vehicle_id: str, event_type: str, data: Any) -> None:
        for listener in list(self._event_listeners):
            try:
                listener(vehicle_id, event_type, data)
            except Exception as exc:
                logger.error("Error in BLE manager event listener: %s", exc)

    async def get_or_create_client(
        self, vehicle_id: str, mac_address: str, pairing_token: str
    ) -> RevoltLiveClient:
        """Get active RevoltLiveClient or create and connect a new instance."""
        if vehicle_id in self._clients:
            client = self._clients[vehicle_id]
            if client.is_connected:
                return client

        # Instantiate revolt_ble_toolkit live client
        client = RevoltLiveClient(
            name_filter="RV400",
            heartbeat_interval=10.0,
            heartbeat_timeout=25.0,
        )

        # Attach custom plugin
        plugin = RevoltDataBlePlugin(vehicle_id=vehicle_id, event_dispatcher=self._on_plugin_event)
        client.register_plugin(plugin)

        self._clients[vehicle_id] = client
        self._plugins[vehicle_id] = plugin

        try:
            await client.connect(address=mac_address)
            await client.pair(pairing_token)
        except LiveClientError as exc:
            logger.warning(
                "Failed to connect/pair vehicle %s (%s): %s", vehicle_id, mac_address, exc
            )

        return client

    async def send_command(
        self, vehicle_id: str, command_type: str, token: str | None = None
    ) -> bool:
        """Send a command (VS_ON, VS_OFF, PAIR) to a connected vehicle."""
        if vehicle_id not in self._clients:
            raise LiveClientError(f"Vehicle {vehicle_id} is not connected")

        client = self._clients[vehicle_id]
        if not client.is_connected or not client.control_characteristic_uuid:
            raise LiveClientError(f"Vehicle {vehicle_id} BLE connection is not active")

        char_uuid = client.control_characteristic_uuid

        if command_type == "PAIR":
            token_val = token or "TOKEN123"
            return await client.pair(token_val)
        elif command_type == "VS_ON":
            req = CommandRequest("cmd_vs_on", char_uuid, b"VS,ON")
            await client.enqueue_command(req)
            return True
        elif command_type == "VS_OFF":
            req = CommandRequest("cmd_vs_off", char_uuid, b"VS,OFF")
            await client.enqueue_command(req)
            return True
        else:
            raise LiveClientError(f"Unsupported command type: {command_type}")

    def get_vehicle_connection_state(self, vehicle_id: str) -> str:
        """Return human-readable connection state for vehicle_id."""
        if vehicle_id not in self._clients:
            return ConnectionState.DISCONNECTED.name
        return self._clients[vehicle_id].connection_state.name

    async def disconnect_vehicle(self, vehicle_id: str) -> None:
        """Cleanly disconnect a vehicle BLE client."""
        if vehicle_id in self._clients:
            client = self._clients.pop(vehicle_id)
            self._plugins.pop(vehicle_id, None)
            await client.disconnect()
