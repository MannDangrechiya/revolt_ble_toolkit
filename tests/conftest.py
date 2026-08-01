"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from revolt_ble_toolkit.config.settings import get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    """Ensure each test observes a freshly loaded settings singleton."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
