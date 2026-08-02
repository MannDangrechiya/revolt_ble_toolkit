"""Authentication and JWT token helper service."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import jwt

from revolt_data.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash password securely using SHA-256 for basic service auth."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    return hash_password(plain_password) == hashed_password


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """Generate JWT access token for user_id."""
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str | None:
    """Decode and validate JWT access token returning user_id."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("sub")
    except Exception:
        return None
