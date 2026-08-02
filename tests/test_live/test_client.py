"""Tests for the live BLE client (Module 10), against a fake Bleak backend — no real hardware."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import ClassVar

import pytest

pytest.importorskip("bleak")

from bleak.exc import BleakError

from revolt_ble_toolkit.core.exceptions import LiveClientError
from revolt_ble_toolkit.live import (
    BlePlugin,
    CommandRequest,
    ConnectionState,
    ConnectionStateEvent,
    NotificationEvent,
    RevoltLiveClient,
    WriteEvent,
)
from revolt_ble_toolkit.live import client as client_module

_KNOWN_SERVICE = client_module.VEHICLE_CONTROL_SERVICE_UUID
_KNOWN_CHAR = client_module.VEHICLE_CONTROL_CHARACTERISTIC_UUID


class _FakeDevice:
    def __init__(self, name: str, address: str) -> None:
        self.name = name
        self.address = address


class _FakeCharacteristic:
    def __init__(self, uuid: str, properties: list[str]) -> None:
        self.uuid = uuid
        self.properties = properties


class _FakeService:
    def __init__(self, uuid: str, characteristics: list[_FakeCharacteristic]) -> None:
        self.uuid = uuid
        self.characteristics = characteristics


class _FakeServices:
    def __init__(self, services: list[_FakeService]) -> None:
        self._services = services
        self._by_uuid = {c.uuid: c for s in services for c in s.characteristics}

    def __iter__(self) -> Iterator[_FakeService]:
        return iter(self._services)

    def __len__(self) -> int:
        return len(self._services)

    def get_characteristic(self, uuid: str) -> _FakeCharacteristic | None:
        return self._by_uuid.get(uuid)


class _FakeClient:
    default_services: ClassVar[list[_FakeService]] = []

    def __init__(
        self,
        address: str,
        disconnected_callback: Callable[[object], None] | None = None,
        **_: object,
    ) -> None:
        self.address = address
        self.disconnected_callback = disconnected_callback
        self._connected = False
        self.services = _FakeServices(_FakeClient.default_services)
        self.notify_callbacks: dict[str, Callable[..., None]] = {}
        self.writes: list[tuple[str, bytes, bool | None]] = []

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, **_: object) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def start_notify(self, uuid: str, callback: Callable[..., None]) -> None:
        self.notify_callbacks[uuid] = callback

    async def write_gatt_char(self, uuid: str, data: bytes, response: bool | None = None) -> None:
        self.writes.append((uuid, bytes(data), response))

    def fire_notification(self, uuid: str, data: bytes) -> None:
        sender = _FakeCharacteristic(uuid, [])
        self.notify_callbacks[uuid](sender, bytearray(data))


class _FakeScanner:
    devices: ClassVar[list[_FakeDevice]] = []

    @staticmethod
    async def discover(timeout: float = 5.0, **_: object) -> list[_FakeDevice]:
        return _FakeScanner.devices


@pytest.fixture(autouse=True)
def _fake_bleak(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(client_module, "BleakClient", _FakeClient)
    monkeypatch.setattr(client_module, "BleakScanner", _FakeScanner)
    _FakeClient.default_services = []
    _FakeScanner.devices = []
    yield


def _control_service(char_uuid: str, properties: list[str]) -> _FakeService:
    return _FakeService(_KNOWN_SERVICE, [_FakeCharacteristic(char_uuid, properties)])


def _fake_of(client: RevoltLiveClient) -> _FakeClient:
    """Narrow client._client (typed as the real BleakClient) to the fake we patched in."""
    fake = client._client
    assert isinstance(fake, _FakeClient)
    return fake


def test_scan_filters_by_name() -> None:
    _FakeScanner.devices = [
        _FakeDevice("RV400-1234", "AA:AA:AA:AA:AA:AA"),
        _FakeDevice("Some Other Device", "BB:BB:BB:BB:BB:BB"),
    ]

    matches = asyncio.run(RevoltLiveClient(name_filter="RV400").scan())

    assert [d.address for d in matches] == ["AA:AA:AA:AA:AA:AA"]


def test_connect_raises_when_no_device_matches() -> None:
    _FakeScanner.devices = []

    with pytest.raises(LiveClientError):
        asyncio.run(RevoltLiveClient().connect())


def test_connect_scans_and_connects_to_first_match() -> None:
    _FakeScanner.devices = [_FakeDevice("RV400-9999", "CC:CC:CC:CC:CC:CC")]
    client = RevoltLiveClient()

    asyncio.run(client.connect())

    assert client.is_connected
    assert _fake_of(client).address == "CC:CC:CC:CC:CC:CC"


def test_connect_wraps_bleak_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing_connect(self: object, **_: object) -> None:
        raise BleakError("device not found")

    monkeypatch.setattr(_FakeClient, "connect", failing_connect)

    with pytest.raises(LiveClientError):
        asyncio.run(RevoltLiveClient().connect("AA:AA:AA:AA:AA:AA"))


def test_connect_by_address_skips_scanning() -> None:
    client = RevoltLiveClient()

    asyncio.run(client.connect("AA:AA:AA:AA:AA:AA"))

    assert client.is_connected


def test_write_before_connect_raises() -> None:
    client = RevoltLiveClient()

    with pytest.raises(LiveClientError):
        asyncio.run(client.write(_KNOWN_CHAR, b"\x01"))


def test_prefers_known_control_characteristic_when_present() -> None:
    other_char = _FakeCharacteristic("11111111-2222-3333-4444-555555555555", ["write", "notify"])
    known_char = _FakeCharacteristic(_KNOWN_CHAR, ["write", "notify"])
    _FakeClient.default_services = [_FakeService(_KNOWN_SERVICE, [known_char, other_char])]
    client = RevoltLiveClient()

    asyncio.run(client.connect("AA:AA:AA:AA:AA:AA"))

    assert client.control_characteristic_uuid == _KNOWN_CHAR


def test_falls_back_to_structural_match_when_known_uuid_absent() -> None:
    different_char = "99999999-8888-7777-6666-555555555555"
    _FakeClient.default_services = [_control_service(different_char, ["write", "notify"])]
    client = RevoltLiveClient()

    asyncio.run(client.connect("AA:AA:AA:AA:AA:AA"))

    assert client.control_characteristic_uuid == different_char


def test_no_control_characteristic_found_leaves_none_and_pair_raises() -> None:
    _FakeClient.default_services = []
    client = RevoltLiveClient()
    asyncio.run(client.connect("AA:AA:AA:AA:AA:AA"))

    assert client.control_characteristic_uuid is None
    with pytest.raises(LiveClientError):
        asyncio.run(client.pair("token"))


def test_write_logs_saves_and_calls_back(tmp_path: Path) -> None:
    _FakeClient.default_services = [_control_service(_KNOWN_CHAR, ["write", "notify"])]
    save_path = tmp_path / "session.jsonl"
    events: list[WriteEvent] = []
    client = RevoltLiveClient(save_path=save_path, on_write=events.append)

    async def scenario() -> None:
        await client.connect("AA:AA:AA:AA:AA:AA")
        await client.write(_KNOWN_CHAR, b"\x01\x02")

    asyncio.run(scenario())

    assert _fake_of(client).writes == [(_KNOWN_CHAR, b"\x01\x02", True)]
    assert len(events) == 1 and events[0].value == b"\x01\x02"
    (line,) = save_path.read_text().splitlines()
    record = json.loads(line)
    assert record == {
        "timestamp": events[0].timestamp.isoformat(),
        "direction": "write",
        "characteristic": _KNOWN_CHAR,
        "value_hex": "0102",
    }


def test_notification_triggers_callback_and_save(tmp_path: Path) -> None:
    _FakeClient.default_services = [_control_service(_KNOWN_CHAR, ["write", "notify"])]
    save_path = tmp_path / "session.jsonl"
    events: list[NotificationEvent] = []
    client = RevoltLiveClient(save_path=save_path, on_notification=events.append)

    async def scenario() -> None:
        await client.connect("AA:AA:AA:AA:AA:AA")
        _fake_of(client).fire_notification(_KNOWN_CHAR, b"hello")

    asyncio.run(scenario())

    assert len(events) == 1
    assert events[0].value == b"hello"
    assert events[0].characteristic_uuid == _KNOWN_CHAR
    (line,) = save_path.read_text().splitlines()
    assert json.loads(line)["direction"] == "notify"


def test_pair_returns_true_when_accepted_arrives() -> None:
    _FakeClient.default_services = [_control_service(_KNOWN_CHAR, ["write", "notify"])]
    client = RevoltLiveClient()

    async def scenario() -> bool:
        await client.connect("AA:AA:AA:AA:AA:AA")

        async def fire_accepted() -> None:
            await asyncio.sleep(0.01)
            _fake_of(client).fire_notification(_KNOWN_CHAR, b"ACCEPTED")

        accepted, _ = await asyncio.gather(client.pair("TOKEN123"), fire_accepted())
        return accepted

    assert asyncio.run(scenario()) is True


def test_pair_returns_false_on_timeout() -> None:
    _FakeClient.default_services = [_control_service(_KNOWN_CHAR, ["write", "notify"])]
    client = RevoltLiveClient()

    async def scenario() -> bool:
        await client.connect("AA:AA:AA:AA:AA:AA")
        return await client.pair("TOKEN123", timeout=0.05)

    assert asyncio.run(scenario()) is False


def test_reconnects_after_unexpected_disconnect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "RECONNECT_DELAY_SECONDS", 0.01)
    client = RevoltLiveClient()

    async def scenario() -> None:
        await client.connect("AA:AA:AA:AA:AA:AA")
        fake = _fake_of(client)
        fake._connected = False
        assert fake.disconnected_callback is not None
        fake.disconnected_callback(fake)
        await asyncio.sleep(0.05)
        assert client.is_connected
        await client.disconnect()

    asyncio.run(scenario())


def test_reconnect_retries_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "RECONNECT_DELAY_SECONDS", 0.01)
    original_connect = _FakeClient.connect
    attempts = 0

    async def flaky_connect(self: _FakeClient, **kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise BleakError("still out of range")
        await original_connect(self, **kwargs)

    client = RevoltLiveClient()

    async def scenario() -> None:
        await client.connect("AA:AA:AA:AA:AA:AA")
        fake = _fake_of(client)
        fake._connected = False
        monkeypatch.setattr(_FakeClient, "connect", flaky_connect)
        assert fake.disconnected_callback is not None
        fake.disconnected_callback(fake)
        await asyncio.sleep(0.15)
        assert client.is_connected
        assert attempts == 2
        await client.disconnect()

    asyncio.run(scenario())


def test_state_machine_and_plugin_integration() -> None:
    _FakeClient.default_services = [_control_service(_KNOWN_CHAR, ["write", "notify"])]
    state_events: list[ConnectionStateEvent] = []
    client = RevoltLiveClient(on_state_change=state_events.append)

    class TestPlugin(BlePlugin):
        name = "TestPlugin"

        def __init__(self) -> None:
            self.states: list[ConnectionState] = []

        def on_state_change(self, event: ConnectionStateEvent) -> None:
            self.states.append(event.new_state)

    plugin = TestPlugin()
    client.register_plugin(plugin)

    async def scenario() -> None:
        await client.connect("AA:AA:AA:AA:AA:AA")
        state: ConnectionState = client.connection_state
        assert state == ConnectionState.CONNECTED
        await client.disconnect()
        assert client.connection_state == ConnectionState.DISCONNECTED

    asyncio.run(scenario())

    assert ConnectionState.CONNECTED in plugin.states
    assert ConnectionState.DISCONNECTED in plugin.states


def test_enqueue_command_via_sdk() -> None:
    _FakeClient.default_services = [_control_service(_KNOWN_CHAR, ["write", "notify"])]
    client = RevoltLiveClient()

    async def scenario() -> None:
        await client.connect("AA:AA:AA:AA:AA:AA")
        req = CommandRequest("cmd_sdk_1", _KNOWN_CHAR, b"\xaa\xbb")
        await client.enqueue_command(req)
        await client.disconnect()

    asyncio.run(scenario())
    assert _fake_of(client).writes == [(_KNOWN_CHAR, b"\xaa\xbb", True)]


