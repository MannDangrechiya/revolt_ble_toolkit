"""Analysis result exporters.

Concrete exporters (e.g. JSON, CSV) are added in a future milestone. This
package currently only exposes the extension point.
"""

from __future__ import annotations

from revolt_ble_toolkit.exporters.base import BaseExporter

__all__ = ["BaseExporter"]
