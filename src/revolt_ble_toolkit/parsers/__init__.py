"""Capture-log parsers.

Concrete parsers (e.g. for Android HCI Snoop Logs) are added in a future
milestone. This package currently only exposes the extension point.
"""

from __future__ import annotations

from revolt_ble_toolkit.parsers.base import BaseLogParser

__all__ = ["BaseLogParser"]
