"""Tests for revolt_data auth service and password hashing."""

from __future__ import annotations

import os
import pytest

# Mock REVOLT_JWT_SECRET before module imports
os.environ.setdefault(
    "REVOLT_JWT_SECRET", "test_secret_key_that_is_at_least_32_bytes_long"
)

from revolt_data.services.auth_service import (
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


def test_decode_invalid_token_returns_none() -> None:
    assert decode_access_token("invalid.jwt.token") is None
