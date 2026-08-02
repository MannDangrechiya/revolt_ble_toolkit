"""Tests for revolt_data configuration settings and REVOLT_JWT_SECRET validation."""

from __future__ import annotations

import os
import pytest

from revolt_data.config import Settings, get_settings


def test_config_missing_jwt_secret_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that missing REVOLT_JWT_SECRET raises ValueError."""
    monkeypatch.delenv("REVOLT_JWT_SECRET", raising=False)
    with pytest.raises(ValueError, match="REVOLT_JWT_SECRET environment variable is required"):
        get_settings()


def test_config_short_jwt_secret_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that REVOLT_JWT_SECRET shorter than 32 bytes raises ValueError."""
    monkeypatch.setenv("REVOLT_JWT_SECRET", "too_short_secret_key")
    with pytest.raises(ValueError, match="at least 32 bytes long"):
        get_settings()


def test_config_valid_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading valid REVOLT_JWT_SECRET from environment."""
    valid_secret = "valid_secret_key_0123456789_32bytes_min"
    monkeypatch.setenv("REVOLT_JWT_SECRET", valid_secret)
    settings = get_settings()
    assert settings.secret_key == valid_secret


def test_settings_explicit_short_secret_raises_value_error() -> None:
    """Test that instantiating Settings with a short secret explicitly raises ValueError."""
    with pytest.raises(ValueError, match="at least 32 bytes long"):
        Settings(secret_key="short_key")
