"""Exception hierarchy for the toolkit.

All toolkit-raised errors derive from :class:`ToolkitError`, letting
callers catch broadly or narrowly as needed (Liskov Substitution).
"""

from __future__ import annotations


class ToolkitError(Exception):
    """Base class for all toolkit-specific errors."""


class ConfigurationError(ToolkitError):
    """Raised when configuration is missing or invalid."""


class ParsingError(ToolkitError):
    """Raised when a capture log cannot be parsed."""


class AnalysisError(ToolkitError):
    """Raised when analysis of parsed records fails."""


class ExportError(ToolkitError):
    """Raised when exporting analysis results fails."""
