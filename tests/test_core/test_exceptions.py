"""Tests for the toolkit's exception hierarchy."""

from __future__ import annotations

import pytest

from revolt_ble_toolkit.core.exceptions import (
    ConfigurationError,
    ExportError,
    LiveClientError,
    ParsingError,
    ToolkitError,
)


@pytest.mark.parametrize(
    "exception_type", [ConfigurationError, ExportError, LiveClientError, ParsingError]
)
def test_every_toolkit_exception_derives_from_toolkit_error(exception_type: type) -> None:
    assert issubclass(exception_type, ToolkitError)


def test_toolkit_error_derives_from_exception() -> None:
    assert issubclass(ToolkitError, Exception)
