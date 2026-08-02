"""Tests for the async write queue."""

from __future__ import annotations

import asyncio

import pytest

from revolt_ble_toolkit.core.exceptions import LiveClientError
from revolt_ble_toolkit.live import AsyncWriteQueue, CommandRequest

_CHAR_UUID = "49535343-1e4d-4bd9-ba61-23c647249616"


def test_write_queue_executes_commands_in_priority_order() -> None:
    executed: list[bytes] = []

    async def mock_handler(char_uuid: str, payload: bytes, response: bool) -> None:
        executed.append(payload)

    queue = AsyncWriteQueue(write_handler=mock_handler)

    async def scenario() -> None:
        queue.start()
        req1 = CommandRequest("cmd1", _CHAR_UUID, b"\x01", priority=10)
        req2 = CommandRequest("cmd2", _CHAR_UUID, b"\x02", priority=1)

        t1 = asyncio.create_task(queue.enqueue(req1))
        t2 = asyncio.create_task(queue.enqueue(req2))
        await asyncio.gather(t1, t2)
        await queue.stop()

    asyncio.run(scenario())

    assert len(executed) == 2
    assert b"\x01" in executed
    assert b"\x02" in executed


def test_write_queue_retries_and_raises_on_failure() -> None:
    attempts = 0

    async def failing_handler(char_uuid: str, payload: bytes, response: bool) -> None:
        nonlocal attempts
        attempts += 1
        raise LiveClientError("Write failed")

    queue = AsyncWriteQueue(write_handler=failing_handler)

    async def scenario() -> None:
        queue.start()
        req = CommandRequest("failing_cmd", _CHAR_UUID, b"\x01", timeout=0.1, retries=2)
        with pytest.raises(LiveClientError, match="failed after 2 attempts"):
            await queue.enqueue(req)
        await queue.stop()

    asyncio.run(scenario())
    assert attempts == 2
