"""
ui.core.dialogs.telemetry_diagnostics_cards — Componentes de Cartões Métricos de Telemetria
========================================================================================
Cartões de diagnóstico compactos e de alto contraste (Design System Lumenia V2).
"""

from __future__ import annotations

from PySide6 import QtWidgets
from ui.core.theme.manager import ThemeManager


class StatCard(QtWidgets.QFrame):
    """Card métrico compacto com rótulo, valor em destaque e unidade."""

    def __init__(self, label: str, initial_value: str = "0", unit: str = "", parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self._unit = unit

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        self.lbl_title = QtWidgets.QLabel(label.upper())
        self.lbl_title.setObjectName("StatTitle")

        self.lbl_value = QtWidgets.QLabel(initial_value)
        self.lbl_value.setObjectName("StatValue")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)

        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

    def set_label(self, label: str) -> None:
        self.lbl_title.setText(label.upper())

    def set_value(self, val_str: str) -> None:
        self.lbl_value.setText(val_str)

    def _apply_theme(self, *args) -> None:
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_panel")
        border = tm.get_color("border")
        muted = tm.get_color("text_sec")
        text = tm.get_color("text_main")

        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QLabel#StatTitle {{
                color: {muted};
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QLabel#StatValue {{
                color: {text};
                font-size: 16px;
                font-weight: bold;
                font-family: monospace;
            }}
        """)
