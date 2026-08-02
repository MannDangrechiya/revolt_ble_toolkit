"""Plugin system for extending live BLE SDK capabilities and event hooks."""

from __future__ import annotations

from typing import Any

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.live.models import ConnectionStateEvent, NotificationEvent, WriteEvent

logger = get_logger(__name__)


class BlePlugin:
    """Base class for custom live BLE SDK plugins."""

    name: str = "BasePlugin"

    def on_state_change(self, event: ConnectionStateEvent) -> None:
        """Called when the client changes connection state."""

    def on_notification(self, event: NotificationEvent) -> None:
        """Called when a raw BLE notification arrives."""

    def on_decoded_payload(self, payload: Any) -> None:
        """Called when a protocol payload is decoded into a model."""

    def on_write(self, event: WriteEvent) -> None:
        """Called when a GATT write command is executed."""


class PluginManager:
    """Manages plugin registration and broadcasts SDK lifecycle events."""

    def __init__(self) -> None:
        self._plugins: list[BlePlugin] = []

    @property
    def registered_plugins(self) -> list[BlePlugin]:
        return list(self._plugins)

    def register(self, plugin: BlePlugin) -> None:
        """Register a plugin."""
        if plugin not in self._plugins:
            self._plugins.append(plugin)
            logger.info("Registered BLE plugin: %s", plugin.name)

    def unregister(self, plugin: BlePlugin) -> None:
        """Unregister a plugin."""
        if plugin in self._plugins:
            self._plugins.remove(plugin)
            logger.info("Unregistered BLE plugin: %s", plugin.name)

    def notify_state_change(self, event: ConnectionStateEvent) -> None:
        """Broadcast state change event to plugins."""
        for plugin in self._plugins:
            try:
                plugin.on_state_change(event)
            except Exception as exc:
                logger.error("Error in plugin %s on_state_change: %s", plugin.name, exc)

    def notify_notification(self, event: NotificationEvent) -> None:
        """Broadcast notification event to plugins."""
        for plugin in self._plugins:
            try:
                plugin.on_notification(event)
            except Exception as exc:
                logger.error("Error in plugin %s on_notification: %s", plugin.name, exc)

    def notify_decoded_payload(self, payload: Any) -> None:
        """Broadcast decoded payload event to plugins."""
        for plugin in self._plugins:
            try:
                plugin.on_decoded_payload(payload)
            except Exception as exc:
                logger.error("Error in plugin %s on_decoded_payload: %s", plugin.name, exc)

    def notify_write(self, event: WriteEvent) -> None:
        """Broadcast write event to plugins."""
        for plugin in self._plugins:
            try:
                plugin.on_write(event)
            except Exception as exc:
                logger.error("Error in plugin %s on_write: %s", plugin.name, exc)
