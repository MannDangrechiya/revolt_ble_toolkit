"""Application configuration settings for revolt_data."""

from __future__ import annotations

from dataclasses import dataclass, field
import os


def _load_jwt_secret() -> str:
    """Load and validate REVOLT_JWT_SECRET environment variable."""
    secret = os.environ.get("REVOLT_JWT_SECRET")
    if not secret:
        raise ValueError("REVOLT_JWT_SECRET environment variable is required")
    if len(secret.encode("utf-8")) < 32:
        raise ValueError("REVOLT_JWT_SECRET must be at least 32 bytes long")
    return secret


@dataclass
class Settings:
    """Core settings for revolt_data service."""

    app_name: str = "revolt_data"
    version: str = "1.0.0"
    debug: bool = False
    secret_key: str = field(default_factory=_load_jwt_secret)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    database_url: str = "sqlite+aiosqlite:///revolt_data.db"
    ble_scan_timeout: float = 10.0
    heartbeat_interval: float = 10.0
    heartbeat_timeout: float = 25.0

    def __post_init__(self) -> None:
        """Validate secret_key on instantiation."""
        if not self.secret_key:
            raise ValueError("REVOLT_JWT_SECRET environment variable is required")
        if len(self.secret_key.encode("utf-8")) < 32:
            raise ValueError("REVOLT_JWT_SECRET must be at least 32 bytes long")


def get_settings() -> Settings:
    """Return app settings."""
    return Settings()
