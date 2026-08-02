"""Application configuration settings for revolt_data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Settings:
    """Core settings for revolt_data service."""

    app_name: str = "revolt_data"
    version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "revolt_data_secret_key_change_in_production_32bytes"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    database_url: str = "sqlite+aiosqlite:///revolt_data.db"
    ble_scan_timeout: float = 10.0
    heartbeat_interval: float = 10.0
    heartbeat_timeout: float = 25.0


def get_settings() -> Settings:
    """Return cached app settings."""
    return Settings()
