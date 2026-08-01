"""Production-grade Live BLE client SDK for the Revolt RV400 vehicle platform.

Features:
- State Machine lifecycle (`ConnectionState`)
- Exponential backoff retry strategy (`RetryStrategy`)
- Prioritized async write queue (`AsyncWriteQueue`)
- Extensible notification manager and protocol payload decoders
- Heartbeat ping and link loss monitoring
- Plugin architecture for protocol extensions (`BlePlugin`)
- Structured event logging and persistence
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.core.exceptions import LiveClientError
from revolt_ble_toolkit.live.heartbeat import HeartbeatManager
from revolt_ble_toolkit.live.models import (
    CommandRequest,
    ConnectionState,
    ConnectionStateEvent,
    NotificationEvent,
    WriteEvent,
)
from revolt_ble_toolkit.live.notification_manager import NotificationManager
from revolt_ble_toolkit.live.plugins import BlePlugin, PluginManager
from revolt_ble_toolkit.live.retry import RetryStrategy
from revolt_ble_toolkit.live.state_machine import ConnectionStateMachine
from revolt_ble_toolkit.live.write_queue import AsyncWriteQueue

logger = get_logger(__name__)

VEHICLE_CONTROL_SERVICE_UUID = "49535343-fe7d-4ae5-8fa9-9fafd205e455"
VEHICLE_CONTROL_CHARACTERISTIC_UUID = "49535343-1e4d-4bd9-ba61-23c647249616"
PAIR_ACCEPTED_RESPONSE = b"ACCEPTED"

DEFAULT_SCAN_TIMEOUT = 10.0
DEFAULT_PAIR_TIMEOUT = 5.0
RECONNECT_DELAY_SECONDS = 3.0


class RevoltLiveClient:
    """Production-grade BLE communication client SDK for the Revolt RV400."""

    def __init__(
        self,
        *,
        name_filter: str = "RV400",
        save_path: str | Path | None = None,
        on_notification: Callable[[NotificationEvent], None] | None = None,
        on_write: Callable[[WriteEvent], None] | None = None,
        on_state_change: Callable[[ConnectionStateEvent], None] | None = None,
        retry_strategy: RetryStrategy | None = None,
        heartbeat_interval: float = 10.0,
        heartbeat_timeout: float = 25.0,
    ) -> None:
        self._name_filter = name_filter.lower()
        self._save_path = Path(save_path) if save_path else None
        self._on_notification_legacy = on_notification
        self._on_write_legacy = on_write

        # SDK Core Components
        self.state_machine = ConnectionStateMachine(ConnectionState.DISCONNECTED)
        if on_state_change:
            self.state_machine.add_listener(on_state_change)

        self.retry_strategy = retry_strategy or RetryStrategy(max_attempts=5, initial_delay=1.0)
        self.notification_manager = NotificationManager()
        self.plugin_manager = PluginManager()
        self.write_queue = AsyncWriteQueue(write_handler=self._execute_raw_write)
        self.heartbeat_manager = HeartbeatManager(
            interval=heartbeat_interval,
            timeout=heartbeat_timeout,
            ping_handler=self._send_heartbeat_ping,
            on_link_loss=self._on_heartbeat_link_loss,
        )

        # Wire notification manager callbacks
        self.notification_manager.subscribe(self._on_notification_event)
        self.notification_manager.subscribe_decoded(self.plugin_manager.notify_decoded_payload)
        self.state_machine.add_listener(self.plugin_manager.notify_state_change)

        # Internal BLE Client State
        self._client: BleakClient | None = None
        self._control_char_uuid: str | None = None
        self._reconnect_address: str | None = None
        self._reconnect_task: asyncio.Task[None] | None = None
        self._closing = False

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    @property
    def connection_state(self) -> ConnectionState:
        return self.state_machine.current_state

    @property
    def control_characteristic_uuid(self) -> str | None:
        """The write+notify characteristic used by :meth:`pair`, once discovered."""
        return self._control_char_uuid

    def register_plugin(self, plugin: BlePlugin) -> None:
        """Register a plugin with the SDK."""
        self.plugin_manager.register(plugin)

    def unregister_plugin(self, plugin: BlePlugin) -> None:
        """Unregister a plugin."""
        self.plugin_manager.unregister(plugin)

    async def scan(self, timeout: float = DEFAULT_SCAN_TIMEOUT) -> list[BLEDevice]:
        """Scan for nearby BLE devices whose advertised name matches the filter."""
        logger.info(
            "Scanning for BLE devices (%.0fs, name contains %r)...", timeout, self._name_filter
        )
        devices = await BleakScanner.discover(timeout=timeout)
        matches = [d for d in devices if d.name and self._name_filter in d.name.lower()]
        logger.info("Found %d matching device(s) out of %d total", len(matches), len(devices))
        return matches

    async def connect(self, address: str | None = None) -> None:
        """Connect to ``address``, or scan and connect to the first name match."""
        if address is None:
            matches = await self.scan()
            if not matches:
                self.state_machine.transition_to(ConnectionState.FAILED, "No device match found")
                raise LiveClientError(f"No BLE device found matching {self._name_filter!r}")
            address = matches[0].address

        self._closing = False
        self._reconnect_address = address
        self.state_machine.transition_to(ConnectionState.CONNECTING, f"Connecting to {address}")

        try:
            await self.retry_strategy.execute(
                lambda: self._connect_once(address),
                retry_exceptions=(LiveClientError,),
            )
        except Exception as exc:
            self.state_machine.transition_to(ConnectionState.FAILED, f"Connection failed: {exc}")
            raise

    async def _connect_once(self, address: str) -> None:
        logger.info("Connecting to %s...", address)
        client = BleakClient(address, disconnected_callback=self._on_disconnected)
        try:
            await client.connect()
        except (BleakError, TimeoutError) as exc:
            raise LiveClientError(f"Failed to connect to {address}: {exc}") from exc

        self._client = client
        logger.info("Connected to %s", address)
        self.state_machine.transition_to(ConnectionState.CONNECTED, f"Connected to {address}")
        await self._discover_and_subscribe()

        # Start SDK background tasks
        self.write_queue.start()
        self.heartbeat_manager.start()

    async def _discover_and_subscribe(self) -> None:
        assert self._client is not None
        services = self._client.services
        logger.info("Discovered %d service(s)", len(list(services)))
        fallback_control_char: str | None = None

        for service in services:
            logger.info("  Service %s", service.uuid)
            for char in service.characteristics:
                logger.info("    Characteristic %s (%s)", char.uuid, ",".join(char.properties))

                if (
                    service.uuid == VEHICLE_CONTROL_SERVICE_UUID
                    and "write" in char.properties
                    and "notify" in char.properties
                    and fallback_control_char is None
                ):
                    fallback_control_char = char.uuid

                if "notify" in char.properties or "indicate" in char.properties:
                    await self._client.start_notify(char.uuid, self._handle_bleak_notification)
                    logger.info("    Subscribed to notifications on %s", char.uuid)

        if services.get_characteristic(VEHICLE_CONTROL_CHARACTERISTIC_UUID) is not None:
            self._control_char_uuid = VEHICLE_CONTROL_CHARACTERISTIC_UUID
        else:
            self._control_char_uuid = fallback_control_char
            if fallback_control_char:
                logger.warning(
                    "Known control characteristic %s not found; falling back to %s",
                    VEHICLE_CONTROL_CHARACTERISTIC_UUID,
                    fallback_control_char,
                )
            else:
                logger.warning("No write+notify control characteristic found on this device")

    def _handle_bleak_notification(self, sender: BleakGATTCharacteristic, data: bytearray) -> None:
        self.heartbeat_manager.mark_activity()
        event = NotificationEvent(
            timestamp=datetime.now(UTC), characteristic_uuid=sender.uuid, value=bytes(data)
        )
        logger.info("NOTIFY %s: %s", event.characteristic_uuid, event.value.hex())
        self.notification_manager.handle_notification(event)

    def _on_notification_event(self, event: NotificationEvent) -> None:
        self._save_event("notify", event.characteristic_uuid, event.value, event.timestamp)
        if self._on_notification_legacy:
            self._on_notification_legacy(event)
        self.plugin_manager.notify_notification(event)

    async def _execute_raw_write(
        self, characteristic_uuid: str, data: bytes, response: bool
    ) -> None:
        if self._client is None or not self._client.is_connected:
            raise LiveClientError("Not connected")
        logger.info("WRITE %s: %s", characteristic_uuid, data.hex())
        await self._client.write_gatt_char(characteristic_uuid, data, response=response)

        event = WriteEvent(
            timestamp=datetime.now(UTC), characteristic_uuid=characteristic_uuid, value=data
        )
        self.heartbeat_manager.mark_activity()
        self._save_event("write", event.characteristic_uuid, event.value, event.timestamp)
        if self._on_write_legacy:
            self._on_write_legacy(event)
        self.plugin_manager.notify_write(event)

    async def write(self, characteristic_uuid: str, data: bytes, *, response: bool = True) -> None:
        """Write ``data`` to a characteristic via the async write queue."""
        request = CommandRequest(
            command_id=f"write_{characteristic_uuid[:8]}_{datetime.now(UTC).timestamp()}",
            characteristic_uuid=characteristic_uuid,
            payload=data,
            requires_response=response,
        )
        await self.enqueue_command(request)

    async def enqueue_command(self, request: CommandRequest) -> None:
        """Enqueue a structured command request into the write queue."""
        if not self.is_connected:
            raise LiveClientError("Not connected")
        await self.write_queue.enqueue(request)

    async def pair(self, token: str, *, timeout: float = DEFAULT_PAIR_TIMEOUT) -> bool:
        """Write the PAIR handshake and wait for an ACCEPTED notification."""
        if self._control_char_uuid is None:
            raise LiveClientError("No write+notify control characteristic discovered")

        self.state_machine.transition_to(
            ConnectionState.AUTHENTICATING, "Initiating PAIR handshake"
        )

        accepted = asyncio.Event()

        def watch(event: NotificationEvent) -> None:
            if event.value == PAIR_ACCEPTED_RESPONSE:
                accepted.set()

        self.notification_manager.subscribe(watch, self._control_char_uuid)
        try:
            await self.write(self._control_char_uuid, f"PAIR{token}#".encode())
            try:
                await asyncio.wait_for(accepted.wait(), timeout=timeout)
                self.state_machine.transition_to(
                    ConnectionState.AUTHENTICATED, "PAIR handshake ACCEPTED"
                )
                return True
            except TimeoutError:
                self.state_machine.transition_to(
                    ConnectionState.CONNECTED, "PAIR handshake timed out"
                )
                return False
        finally:
            self.notification_manager.unsubscribe(watch, self._control_char_uuid)

    async def _send_heartbeat_ping(self) -> None:
        if self.is_connected and self._control_char_uuid:
            await self._execute_raw_write(self._control_char_uuid, b"\x01", response=False)

    def _on_heartbeat_link_loss(self) -> None:
        if not self._closing and self.is_connected:
            logger.warning("Link loss detected via heartbeat timeout; initiating reconnect...")
            self._on_disconnected(self._client)  # type: ignore[arg-type]

    def _on_disconnected(self, client: BleakClient) -> None:
        logger.warning("Disconnected from %s", client.address if client else "device")
        self._closing_tasks = [
            asyncio.create_task(self.write_queue.stop()),
            asyncio.create_task(self.heartbeat_manager.stop()),
        ]

        if not self._closing and self._reconnect_address:
            self.state_machine.transition_to(
                ConnectionState.RECONNECTING, "Unexpected disconnect"
            )
            self._reconnect_task = asyncio.create_task(self._reconnect())
        else:
            self.state_machine.transition_to(
                ConnectionState.DISCONNECTED, "Clean disconnect"
            )

    async def _reconnect(self) -> None:
        attempt = 1
        while not self._closing:
            delay = (
                self.retry_strategy.get_delay(attempt)
                if RECONNECT_DELAY_SECONDS == 3.0
                else RECONNECT_DELAY_SECONDS
            )
            logger.warning(
                "Reconnect attempt %d in %.2fs to %s...", attempt, delay, self._reconnect_address
            )
            await asyncio.sleep(delay)
            assert self._reconnect_address is not None
            try:
                await self._connect_once(self._reconnect_address)
                logger.info("Reconnected to %s", self._reconnect_address)
                return
            except LiveClientError:
                attempt += 1

    def _save_event(self, direction: str, char_uuid: str, value: bytes, ts: datetime) -> None:
        if self._save_path is None:
            return
        record = {
            "timestamp": ts.isoformat(),
            "direction": direction,
            "characteristic": char_uuid,
            "value_hex": value.hex(),
        }
        with self._save_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    async def disconnect(self) -> None:
        self._closing = True
        self.state_machine.transition_to(ConnectionState.DISCONNECTING, "User disconnect")
        await self.write_queue.stop()
        await self.heartbeat_manager.stop()

        if self._client is not None:
            await self._client.disconnect()

        self.state_machine.transition_to(ConnectionState.DISCONNECTED, "Disconnected")
