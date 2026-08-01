"""Application configuration model and loader.

Layered override strategy (later wins):

1. Hard-coded defaults defined on the dataclasses below.
2. Values from an optional TOML file (``config/default.toml`` by default).
3. Environment variables prefixed with ``REVOLT_`` (highest priority).

Consumers depend on the immutable :class:`AppSettings` abstraction returned
by :func:`get_settings` rather than reading files or environment variables
directly, keeping configuration concerns isolated from the rest of the
toolkit (Dependency Inversion / Single Responsibility).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

_ENV_PREFIX = "REVOLT_"
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CONFIG_FILE = _PROJECT_ROOT / "config" / "default.toml"
_DEFAULT_ENVIRONMENT = "development"
_DEFAULT_DEBUG = False


@dataclass(frozen=True, slots=True)
class PathSettings:
    """Filesystem locations used by the toolkit."""

    project_root: Path = _PROJECT_ROOT
    data_dir: Path = _PROJECT_ROOT / "data"
    log_dir: Path = _PROJECT_ROOT / "logs"
    reports_dir: Path = _PROJECT_ROOT / "reports"


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    """Controls for the logging subsystem."""

    level: str = "INFO"
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    log_to_file: bool = True
    log_file_name: str = "revolt_ble_toolkit.log"
    max_bytes: int = 5 * 1024 * 1024
    backup_count: int = 3


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Root, immutable application configuration."""

    environment: str = _DEFAULT_ENVIRONMENT
    debug: bool = _DEFAULT_DEBUG
    paths: PathSettings = field(default_factory=PathSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _coerce(raw_value: str, reference: Any) -> Any:
    """Coerce an environment variable string to the type of ``reference``."""
    if isinstance(reference, bool):
        return raw_value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(reference, int):
        return int(raw_value)
    if isinstance(reference, Path):
        return Path(raw_value)
    return raw_value


def _settings_from_mapping(data: dict[str, Any]) -> AppSettings:
    """Build an :class:`AppSettings` from a TOML-derived mapping."""
    paths_data = data.get("paths", {})
    logging_data = data.get("logging", {})
    path_field_names = {f.name for f in fields(PathSettings)}
    logging_field_names = {f.name for f in fields(LoggingSettings)}

    return AppSettings(
        environment=data.get("environment", _DEFAULT_ENVIRONMENT),
        debug=data.get("debug", _DEFAULT_DEBUG),
        paths=PathSettings(**{k: Path(v) for k, v in paths_data.items() if k in path_field_names}),
        logging=LoggingSettings(
            **{k: v for k, v in logging_data.items() if k in logging_field_names}
        ),
    )


def _apply_env_overrides(settings: AppSettings) -> AppSettings:
    """Overlay ``REVOLT_*`` environment variables onto ``settings``."""
    updates: dict[str, Any] = {}
    for key in ("environment", "debug"):
        env_key = f"{_ENV_PREFIX}{key.upper()}"
        if env_key in os.environ:
            updates[key] = _coerce(os.environ[env_key], getattr(settings, key))

    logging_updates: dict[str, Any] = {}
    for f in fields(LoggingSettings):
        env_key = f"{_ENV_PREFIX}LOGGING_{f.name.upper()}"
        if env_key in os.environ:
            current = getattr(settings.logging, f.name)
            logging_updates[f.name] = _coerce(os.environ[env_key], current)
    if logging_updates:
        updates["logging"] = replace(settings.logging, **logging_updates)

    return replace(settings, **updates) if updates else settings


@lru_cache(maxsize=1)
def get_settings(config_path: Path | None = None) -> AppSettings:
    """Return the cached, immutable application settings singleton.

    :param config_path: Optional override for the TOML config file location.
        Defaults to ``config/default.toml`` at the project root.
    """
    toml_data = _read_toml(config_path or _DEFAULT_CONFIG_FILE)
    settings = _settings_from_mapping(toml_data) if toml_data else AppSettings()
    return _apply_env_overrides(settings)
