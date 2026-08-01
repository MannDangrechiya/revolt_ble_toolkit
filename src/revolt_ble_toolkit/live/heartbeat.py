"""Heartbeat and link-loss monitoring manager."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

from revolt_ble_toolkit.config.logging_config import get_logger

logger = get_logger(__name__)


class HeartbeatManager:
    """Sends periodic heartbeats and monitors link activity to detect lost connections."""

    def __init__(
        self,
        *,
        interval: float = 10.0,
        timeout: float = 25.0,
        ping_handler: Callable[[], Awaitable[None]] | None = None,
        on_link_loss: Callable[[], None] | None = None,
    ) -> None:
        self.interval = interval
        self.timeout = timeout
        self._ping_handler = ping_handler
        self._on_link_loss = on_link_loss
        self._last_activity = 0.0
        self._monitor_task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def mark_activity(self) -> None:
        """Mark connection activity timestamp."""
        loop = asyncio.get_running_loop()
        self._last_activity = loop.time()

    def start(self) -> None:
        """Start the heartbeat ping and link-loss monitoring background task."""
        if not self._running:
            self._running = True
            loop = asyncio.get_running_loop()
            self._last_activity = loop.time()
            self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop the heartbeat manager background task."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task
            self._monitor_task = None

    async def _monitor_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.interval)
            loop = asyncio.get_running_loop()
            now = loop.time()
            elapsed_since_activity = now - self._last_activity

            if elapsed_since_activity >= self.timeout:
                logger.warning(
                    "Heartbeat timeout: no BLE activity for %.1fs (threshold %.1fs)",
                    elapsed_since_activity,
                    self.timeout,
                )
                if self._on_link_loss:
                    try:
                        self._on_link_loss()
                    except Exception as exc:
                        logger.error("Error in link loss callback: %s", exc)
                break

            if self._ping_handler is not None:
                try:
                    logger.debug("Sending heartbeat ping...")
                    await self._ping_handler()
                    self.mark_activity()
                except Exception as exc:
                    logger.warning("Heartbeat ping failed: %s", exc)
