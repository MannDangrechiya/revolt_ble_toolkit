"""Async write queue for serializing and retrying GATT write operations."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

from revolt_ble_toolkit.config.logging_config import get_logger
from revolt_ble_toolkit.core.exceptions import LiveClientError
from revolt_ble_toolkit.live.models import CommandRequest

logger = get_logger(__name__)

QueueItem = tuple[int, int, CommandRequest, asyncio.Future[None]]


class AsyncWriteQueue:
    """Async queue that processes GATT write commands serially with timeouts and retries."""

    def __init__(
        self,
        write_handler: Callable[[str, bytes, bool], Awaitable[None]],
    ) -> None:
        self._write_handler = write_handler
        self._queue: asyncio.PriorityQueue[QueueItem] = asyncio.PriorityQueue()
        self._worker_task: asyncio.Task[None] | None = None
        self._running = False
        self._sequence = 0

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the background worker task."""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._process_queue())

    async def stop(self) -> None:
        """Stop the background worker task and cancel pending items."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None

        # Cancel remaining pending futures
        while not self._queue.empty():
            _, _, req, future = self._queue.get_nowait()
            if not future.done():
                err_msg = f"Write queue stopped for command {req.command_id}"
                future.set_exception(LiveClientError(err_msg))

    async def enqueue(self, request: CommandRequest) -> None:
        """Enqueue a command request and await its completion."""
        if not self._running:
            raise LiveClientError("Write queue is not running")

        loop = asyncio.get_running_loop()
        future: asyncio.Future[None] = loop.create_future()
        self._sequence += 1
        await self._queue.put((request.priority, self._sequence, request, future))
        await future

    async def _process_queue(self) -> None:
        while self._running:
            try:
                _, _, request, future = await self._queue.get()
            except asyncio.CancelledError:
                break

            if future.done():
                self._queue.task_done()
                continue

            try:
                await self._execute_command_with_retries(request)
                if not future.done():
                    future.set_result(None)
            except Exception as exc:
                if not future.done():
                    future.set_exception(exc)
            finally:
                self._queue.task_done()

    async def _execute_command_with_retries(self, request: CommandRequest) -> None:
        attempt = 1
        last_error: Exception | None = None

        while attempt <= request.retries:
            try:
                logger.debug(
                    "Executing write command %s (attempt %d/%d)...",
                    request.command_id,
                    attempt,
                    request.retries,
                )
                await asyncio.wait_for(
                    self._write_handler(
                        request.characteristic_uuid,
                        request.payload,
                        request.requires_response,
                    ),
                    timeout=request.timeout,
                )
                logger.debug("Write command %s completed successfully", request.command_id)
                return
            except (TimeoutError, LiveClientError, OSError) as exc:
                last_error = exc
                logger.warning(
                    "Write command %s attempt %d/%d failed: %s",
                    request.command_id,
                    attempt,
                    request.retries,
                    exc,
                )
                attempt += 1
                if attempt <= request.retries:
                    await asyncio.sleep(0.1 * attempt)

        raise LiveClientError(
            f"Command {request.command_id} failed after {request.retries} attempts: {last_error}"
        ) from last_error
