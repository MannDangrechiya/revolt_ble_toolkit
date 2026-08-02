"""Tests for revolt_data CORS configuration and _get_cors_origins."""

from __future__ import annotations

import os
import pytest

from revolt_data.main import _get_cors_origins, create_app


def test_cors_origins_empty_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test default CORS origins is empty list in non-dev environment."""
    monkeypatch.delenv("REVOLT_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("REVOLT_ENV", raising=False)
    origins = _get_cors_origins()
    assert origins == []


def test_cors_origins_parsed_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test parsing comma-separated origins from REVOLT_CORS_ORIGINS."""
    monkeypatch.setenv("REVOLT_CORS_ORIGINS", "https://app.example.com, https://admin.example.com")
    monkeypatch.delenv("REVOLT_ENV", raising=False)
    origins = _get_cors_origins()
    assert origins == ["https://app.example.com", "https://admin.example.com"]


def test_cors_origins_wildcard_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that wildcard origin '*' is stripped when credentials are enabled."""
    monkeypatch.setenv("REVOLT_CORS_ORIGINS", "*, https://app.example.com")
    monkeypatch.delenv("REVOLT_ENV", raising=False)
    origins = _get_cors_origins()
    assert "*" not in origins
    assert origins == ["https://app.example.com"]


def test_cors_origins_dev_mode_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that REVOLT_ENV=dev automatically includes localhost origins."""
    monkeypatch.delenv("REVOLT_CORS_ORIGINS", raising=False)
    monkeypatch.setenv("REVOLT_ENV", "dev")
    origins = _get_cors_origins()
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:8000" in origins


def test_create_app_cors_middleware() -> None:
    """Test create_app succeeds with updated CORS middleware."""
    os.environ.setdefault(
        "REVOLT_JWT_SECRET", "test_secret_key_that_is_at_least_32_bytes_long"
    )
    app = create_app()
    assert app is not None
