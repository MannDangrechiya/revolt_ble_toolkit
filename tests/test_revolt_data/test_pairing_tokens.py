"""Tests for Fernet pairing token encryption, decryption, and fail-closed BLE manager behavior."""

from __future__ import annotations

import asyncio
import os
import pytest
from cryptography.fernet import Fernet

# Setup environment variables for test execution
test_fernet_key = Fernet.generate_key().decode("utf-8")
os.environ.setdefault("REVOLT_ENCRYPTION_KEY", test_fernet_key)
os.environ.setdefault(
    "REVOLT_JWT_SECRET", "test_secret_key_that_is_at_least_32_bytes_long"
)

from revolt_ble_toolkit.core.exceptions import LiveClientError
from revolt_data.services.ble_manager import LiveBleManager
from revolt_data.services.crypto import decrypt_token, encrypt_token


def test_encrypt_decrypt_token_roundtrip() -> None:
    """Test encrypting and decrypting a pairing token."""
    raw_token = "MY_SECRET_PAIR_TOKEN_123"
    encrypted = encrypt_token(raw_token)
    assert encrypted != raw_token
    decrypted = decrypt_token(encrypted)
    assert decrypted == raw_token


def test_encrypt_empty_token_raises_error() -> None:
    """Test that encrypting an empty token raises ValueError."""
    with pytest.raises(ValueError, match="Cannot encrypt an empty token"):
        encrypt_token("")


def test_decrypt_empty_token_raises_error() -> None:
    """Test that decrypting an empty token raises ValueError."""
    with pytest.raises(ValueError, match="Pairing token is required and cannot be empty"):
        decrypt_token("")


def test_send_command_pair_fails_closed_without_token() -> None:
    """Test that send_command PAIR raises ValueError when token is missing (no TOKEN123 fallback)."""
    manager = LiveBleManager()

    class DummyClient:
        is_connected = True
        control_characteristic_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"

    manager._clients["v999"] = DummyClient()  # type: ignore[assignment]

    with pytest.raises(ValueError, match="Pairing token is required"):
        asyncio.run(manager.send_command("v999", "PAIR", token=None))
