"""Tests for the retry strategy manager."""

from __future__ import annotations

import asyncio

import pytest

from revolt_ble_toolkit.live import RetryStrategy


def test_retry_delay_calculation() -> None:
    retry = RetryStrategy(initial_delay=1.0, max_delay=10.0, backoff_factor=2.0, jitter=False)
    assert retry.get_delay(1) == 1.0
    assert retry.get_delay(2) == 2.0
    assert retry.get_delay(3) == 4.0
    assert retry.get_delay(4) == 8.0
    assert retry.get_delay(5) == 10.0  # Capped by max_delay


def test_execute_retries_until_success() -> None:
    retry = RetryStrategy(max_attempts=3, initial_delay=0.01, jitter=False)
    attempts = 0

    async def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("Temporary failure")
        return "success"

    result = asyncio.run(retry.execute(flaky))
    assert result == "success"
    assert attempts == 3


def test_execute_raises_when_max_attempts_exceeded() -> None:
    retry = RetryStrategy(max_attempts=2, initial_delay=0.01, jitter=False)

    async def failing() -> None:
        raise ValueError("Permanent failure")

    with pytest.raises(ValueError, match="Permanent failure"):
        asyncio.run(retry.execute(failing))
