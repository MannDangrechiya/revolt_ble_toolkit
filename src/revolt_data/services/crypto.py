"""Fernet encryption utilities for revolt_data sensitive fields."""

from __future__ import annotations

import base64
import os
from cryptography.fernet import Fernet


def get_fernet_key() -> str:
    """Retrieve REVOLT_ENCRYPTION_KEY from environment or raise ValueError."""
    key = os.environ.get("REVOLT_ENCRYPTION_KEY")
    if not key:
        raise ValueError("REVOLT_ENCRYPTION_KEY environment variable is required")
    return key


def _get_fernet() -> Fernet:
    key = get_fernet_key()
    try:
        return Fernet(key.encode("utf-8"))
    except Exception:
        key_bytes = key.encode("utf-8")
        if len(key_bytes) < 32:
            raise ValueError("REVOLT_ENCRYPTION_KEY must be at least 32 bytes long") from None
        valid_key = base64.urlsafe_b64encode(key_bytes[:32])
        return Fernet(valid_key)


def encrypt_token(raw_token: str) -> str:
    """Encrypt a plaintext pairing token at rest using Fernet."""
    if not raw_token:
        raise ValueError("Cannot encrypt an empty token")
    fernet = _get_fernet()
    return fernet.encrypt(raw_token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a Fernet encrypted pairing token at point of use."""
    if not encrypted_token:
        raise ValueError("Pairing token is required and cannot be empty")
    fernet = _get_fernet()
    try:
        return fernet.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise ValueError(f"Failed to decrypt pairing token: {exc}") from exc
