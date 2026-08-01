"""Tests for the configuration loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from revolt_ble_toolkit.config.settings import AppSettings, get_settings
from revolt_ble_toolkit.core.exceptions import ConfigurationError


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


def test_missing_config_file_falls_back_to_defaults(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.toml"

    settings = get_settings(missing)

    assert settings == AppSettings()


def test_malformed_toml_raises_configuration_error(tmp_path: Path) -> None:
    bad_config = tmp_path / "bad.toml"
    bad_config.write_text("this is not [valid toml", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="invalid TOML"):
        get_settings(bad_config)


def test_env_override_bool_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLT_DEBUG", "true")

    assert get_settings().debug is True


def test_env_override_str_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLT_ENVIRONMENT", "production")

    assert get_settings().environment == "production"


def test_env_override_nested_logging_str_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLT_LOGGING_LEVEL", "DEBUG")

    assert get_settings().logging.level == "DEBUG"


def test_env_override_nested_logging_int_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLT_LOGGING_BACKUP_COUNT", "7")

    assert get_settings().logging.backup_count == 7


def test_env_override_nested_logging_bool_field(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLT_LOGGING_LOG_TO_FILE", "false")

    assert get_settings().logging.log_to_file is False
