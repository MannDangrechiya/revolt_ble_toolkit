"""Tests confirming the extension-point base classes stay abstract."""

from __future__ import annotations

import pytest

from revolt_ble_toolkit.analyzers.base import BaseAnalyzer
from revolt_ble_toolkit.exporters.base import BaseExporter
from revolt_ble_toolkit.parsers.base import BaseLogParser


@pytest.mark.parametrize("base_class", [BaseLogParser, BaseAnalyzer, BaseExporter])
def test_base_class_cannot_be_instantiated(base_class: type) -> None:
    with pytest.raises(TypeError):
        base_class()
