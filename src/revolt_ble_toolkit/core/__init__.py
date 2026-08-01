"""Core domain layer: the toolkit-wide exception hierarchy.

Every toolkit-raised error derives from :class:`ToolkitError`. There is no
generic parser/analyzer/exporter interface layer here: each concrete module
(``parsers.btsnoop``, ``parsers.att``, ``analyzers.gatt``, ``analyzers.protocol``,
``analyzers.compare``, ``exporters.capture_report``) defines its own rich,
strongly-typed models instead of conforming to a shared envelope — none of
them ended up needing one, so keeping a speculative one around would just be
unused abstraction (see the v1.0 audit for why it was removed).
"""

from __future__ import annotations

from revolt_ble_toolkit.core.exceptions import (
    ConfigurationError,
    ExportError,
    LiveClientError,
    ParsingError,
    ToolkitError,
)

__all__ = [
    "ConfigurationError",
    "ExportError",
    "LiveClientError",
    "ParsingError",
    "ToolkitError",
]
