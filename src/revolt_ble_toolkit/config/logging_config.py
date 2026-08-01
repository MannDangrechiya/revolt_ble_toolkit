"""Logging configuration for the toolkit.

Centralizes logger setup so every module obtains a correctly configured
logger via :func:`get_logger`, keeping formatting and handler wiring in a
single place (Single Responsibility Principle).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from revolt_ble_toolkit.config.settings import AppSettings, get_settings

_ROOT_LOGGER_NAME = "revolt_ble_toolkit"
_configured = False


def configure_logging(settings: AppSettings | None = None) -> None:
    """Configure the package's root logger. Safe to call more than once."""
    global _configured
    if _configured:
        return

    settings = settings or get_settings()
    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.setLevel(settings.logging.level)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt=settings.logging.format,
        datefmt=settings.logging.date_format,
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if settings.logging.log_to_file:
        log_dir = settings.paths.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / settings.logging.log_file_name,
            maxBytes=settings.logging.max_bytes,
            backupCount=settings.logging.backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger namespaced under the package's root logger."""
    configure_logging()
    return logging.getLogger(name)
