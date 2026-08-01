"""Live BLE client for the Revolt RV400, using Bleak.

Scans for the vehicle by advertised name, connects, discovers its GATT
services, and subscribes to every notify-capable characteristic found —
notifications are exposed exactly as received, with no telemetry parsing
or interpretation here (see ``analyzers.compare`` if you want heuristic
correlation applied to *captured* logs instead).

The vehicle control service/characteristic UUIDs below are empirically
confirmed from a real RV400 capture (see ``analyzers.gatt``'s output on
that capture: service handles 80-88, characteristic value_handle=82 with
WRITE|NOTIFY, observed carrying "PAIR...#" writes and "ACCEPTED"/telemetry
notifications) — not guessed. If a different firmware doesn't have this
exact characteristic, discovery falls back to the first write+notify
characteristic in that service; if even the service is absent, the control
characteristic is left unset and :meth:`pair`/callers relying on it will
get a clear :class:`LiveClientError` rather than a silent no-op.

The PAIR handshake's *mechanics* are implemented (write ``PAIR<token>#``,
wait for an ``ACCEPTED`` notification) but the token itself is never
derived or guessed — callers supply whatever token their vehicle expects.
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
from revolt_ble_toolkit.live.models import NotificationEvent, WriteEvent

logger = get_logger(__name__)

VEHICLE_CONTROL_SERVICE_UUID = "49535343-fe7d-4ae5-8fa9-9fafd205e455"
VEHICLE_CONTROL_CHARACTERISTIC_UUID = "49535343-1e4d-4bd9-ba61-23c647249616"
PAIR_ACCEPTED_RESPONSE = b"ACCEPTED"

DEFAULT_SCAN_TIMEOUT = 10.0
DEFAULT_PAIR_TIMEOUT = 5.0
RECONNECT_DELAY_SECONDS = 3.0


class RevoltLiveClient:
    """Connects to a Revolt RV400 over BLE and streams every notification."""

    def __init__(
        self,
        *,
        name_filter: str = "RV400",
        save_path: str | Path | None = None,
        on_notification: Callable[[NotificationEvent], None] | None = None,
        on_write: Callable[[WriteEvent], None] | None = None,
    ) -> None:
        self._name_filter = name_filter.lower()
        self._client: BleakClient | None = None
        self._control_char_uuid: str | None = None
        self._on_notification = on_notification
        self._on_write = on_write
        self._save_path = Path(save_path) if save_path else None
        self._reconnect_address: str | None = None
        self._reconnect_task: asyncio.Task[None] | None = None
        self._closing = False

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    @property
    def control_characteristic_uuid(self) -> str | None:
        """The write+notify characteristic used by :meth:`pair`, once discovered."""
        return self._control_char_uuid

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
                raise LiveClientError(f"No BLE device found matching {self._name_filter!r}")
            address = matches[0].address

        self._closing = False
        self._reconnect_address = address
        await self._connect_once(address)

    async def _connect_once(self, address: str) -> None:
        logger.info("Connecting to %s...", address)
        client = BleakClient(address, disconnected_callback=self._on_disconnected)
        try:
            await client.connect()
        except (BleakError, TimeoutError) as exc:
            raise LiveClientError(f"Failed to connect to {address}: {exc}") from exc
        self._client = client
        logger.info("Connected to %s", address)
        await self._discover_and_subscribe()

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
                    await self._client.start_notify(char.uuid, self._handle_notification)
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

    def _handle_notification(self, sender: BleakGATTCharacteristic, data: bytearray) -> None:
        event = NotificationEvent(
            timestamp=datetime.now(UTC), characteristic_uuid=sender.uuid, value=bytes(data)
        )
        logger.info("NOTIFY %s: %s", event.characteristic_uuid, event.value.hex())
        self._save_event("notify", event.characteristic_uuid, event.value, event.timestamp)
        if self._on_notification:
            self._on_notification(event)

    async def write(self, characteristic_uuid: str, data: bytes, *, response: bool = True) -> None:
        """Write ``data`` to a characteristic; logs, saves, and calls back like a notification."""
        if self._client is None or not self._client.is_connected:
            raise LiveClientError("Not connected")
        logger.info("WRITE %s: %s", characteristic_uuid, data.hex())
        await self._client.write_gatt_char(characteristic_uuid, data, response=response)
        event = WriteEvent(
            timestamp=datetime.now(UTC), characteristic_uuid=characteristic_uuid, value=data
        )
        self._save_event("write", event.characteristic_uuid, event.value, event.timestamp)
        if self._on_write:
            self._on_write(event)

    async def pair(self, token: str, *, timeout: float = DEFAULT_PAIR_TIMEOUT) -> bool:
        """Write the PAIR handshake and wait for an ACCEPTED notification.

        ``token`` is supplied by the caller — this does not derive or guess it.
        Returns True if ACCEPTED arrived within ``timeout``, False otherwise.
        """
        if self._control_char_uuid is None:
            raise LiveClientError("No write+notify control characteristic discovered")

        accepted = asyncio.Event()
        previous_callback = self._on_notification

        def watch(event: NotificationEvent) -> None:
            if event.value == PAIR_ACCEPTED_RESPONSE:
                accepted.set()
            if previous_callback:
                previous_callback(event)

        self._on_notification = watch
        try:
            await self.write(self._control_char_uuid, f"PAIR{token}#".encode())
            try:
                await asyncio.wait_for(accepted.wait(), timeout=timeout)
            except TimeoutError:
                return False
            return True
        finally:
            self._on_notification = previous_callback

    def _on_disconnected(self, client: BleakClient) -> None:
        logger.warning("Disconnected from %s", client.address)
        if not self._closing and self._reconnect_address:
            self._reconnect_task = asyncio.ensure_future(self._reconnect())

    async def _reconnect(self) -> None:
        # ponytail: fixed-delay infinite retry, no backoff cap. Add
        # exponential backoff + a max-attempts limit if this ever hammers a
        # device that's genuinely gone for good rather than briefly out of range.
        while not self._closing:
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
            assert self._reconnect_address is not None
            try:
                await self._connect_once(self._reconnect_address)
                logger.info("Reconnected to %s", self._reconnect_address)
                return
            except LiveClientError:
                logger.warning("Reconnect failed, retrying in %.0fs", RECONNECT_DELAY_SECONDS)

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
        if self._client is not None:
            await self._client.disconnect()
