"""Exponential backoff and retry strategy manager for live BLE operations."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from revolt_ble_toolkit.config.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RetryStrategy:
    """Configurable exponential backoff and retry strategy manager."""

    def __init__(

        self,
        *,
        max_attempts: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ) -> None:
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate backoff delay for the given 1-based attempt index."""
        if attempt <= 1:
            delay = self.initial_delay
        else:
            delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))

        delay = min(delay, self.max_delay)

        if self.jitter:
            delay = delay * (0.8 + 0.4 * random.random())

        return round(delay, 3)

    async def execute(
        self,
        func: Callable[[], Awaitable[T]],
        *,
        on_retry: Callable[[int, Exception, float], None] | None = None,
        retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> T:
        """Execute an async operation with exponential backoff retries."""
        attempt = 1
        while True:
            try:
                return await func()
            except retry_exceptions as exc:
                if attempt >= self.max_attempts:
                    logger.error("Operation failed after %d attempts: %s", attempt, exc)
                    raise exc

                delay = self.get_delay(attempt)
                logger.warning(
                    "Attempt %d/%d failed (%s); retrying in %.2fs...",
                    attempt,
                    self.max_attempts,
                    exc,
                    delay,
                )

                if on_retry:
                    on_retry(attempt, exc, delay)

                await asyncio.sleep(delay)
                attempt += 1
