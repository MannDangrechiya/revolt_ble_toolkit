"""Filesystem helper utilities."""

from __future__ import annotations

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Create the directory (and any parents) if missing, returning it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return Path(__file__).resolve().parents[3]
