"""Tests for the configuration loader."""

from __future__ import annotations

import pytest

from revolt_ble_toolkit.config.settings import AppSettings, get_settings


def test_get_settings_returns_app_settings() -> None:
    settings = get_settings()
    assert isinstance(settings, AppSettings)


def test_default_logging_level_is_info() -> None:
    settings = get_settings()
    assert settings.logging.level == "INFO"


def test_settings_is_immutable() -> None:
    settings = get_settings()
    with pytest.raises(AttributeError):
        settings.debug = True  # type: ignore[misc]
