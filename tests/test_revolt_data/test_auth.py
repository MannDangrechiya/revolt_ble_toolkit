"""Tests for revolt_data auth service, password hashing, and explicit JWT error handling."""

from __future__ import annotations

import os
from datetime import timedelta
import pytest

# Mock REVOLT_JWT_SECRET before module imports
os.environ.setdefault(
    "REVOLT_JWT_SECRET", "test_secret_key_that_is_at_least_32_bytes_long"
)

from revolt_data.services.auth_service import (
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing() -> None:
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrongpass", hashed) is False


def test_jwt_token_encoding_decoding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "REVOLT_JWT_SECRET", "mocked_secret_key_with_at_least_32_bytes_len"
    )
    token = create_access_token("user_id_123")
    decoded = decode_access_token(token)
    assert decoded == "user_id_123"


def test_decode_invalid_token_raises_token_invalid_error() -> None:
    """Test that invalid or tampered JWT token raises TokenInvalidError."""
    with pytest.raises(TokenInvalidError, match="Invalid or tampered token"):
        decode_access_token("invalid.jwt.token")


def test_decode_expired_token_raises_token_expired_error() -> None:
    """Test that expired JWT token raises TokenExpiredError."""
    token = create_access_token("user_id_123", expires_delta=timedelta(seconds=-10))
    with pytest.raises(TokenExpiredError, match="Token has expired"):
        decode_access_token(token)
