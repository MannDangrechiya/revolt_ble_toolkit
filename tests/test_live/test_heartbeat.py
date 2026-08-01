"""Tests for the heartbeat and link-loss manager."""

from __future__ import annotations

import asyncio

from revolt_ble_toolkit.live import HeartbeatManager


def test_heartbeat_manager_triggers_link_loss_on_timeout() -> None:
    link_lost = False

    def on_loss() -> None:
        nonlocal link_lost
        link_lost = True

    hm = HeartbeatManager(interval=0.01, timeout=0.05, on_link_loss=on_loss)

    async def scenario() -> None:
        hm.start()
        await asyncio.sleep(0.1)
        await hm.stop()

    asyncio.run(scenario())
    assert link_lost is True


def test_heartbeat_manager_ping_handler_called() -> None:
    pinged = False

    async def ping() -> None:
        nonlocal pinged
        pinged = True

    hm = HeartbeatManager(interval=0.01, timeout=1.0, ping_handler=ping)

    async def scenario() -> None:
        hm.start()
        await asyncio.sleep(0.03)
        await hm.stop()

    asyncio.run(scenario())
    assert pinged is True
