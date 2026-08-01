"""Entry point for the Revolt BLE Toolkit desktop GUI.

Usage: ``revolt-ble-gui [path/to/btsnoop_hci.log]``
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from revolt_ble_toolkit.gui.main_window import MainWindow


def _apply_dark_theme(app: QApplication) -> None:
    """Standard Fusion dark palette — no custom stylesheet needed."""
    app.setStyle("Fusion")
    palette = QPalette()
    text = QColor(220, 220, 220)
    palette.setColor(QPalette.ColorRole.Window, QColor(37, 37, 38))
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.ToolTipBase, text)
    palette.setColor(QPalette.ColorRole.ToolTipText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 80, 80))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(38, 122, 199))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127)
    )
    app.setPalette(palette)


def main() -> int:
    app = QApplication(sys.argv)
    _apply_dark_theme(app)

    window = MainWindow()
    window.show()
    if len(sys.argv) > 1:
        window.load_capture(Path(sys.argv[1]))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
