"""
PanelCardBox — Caixa/Cartão Padronizado de Design System para Painéis V2
========================================================================
Fornece uma moldura de cartão ("box") elegante, padronizada e responsiva
para envolver os painéis dentro das gavetas do Lumenia V2.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager


class PanelCardBox(QtWidgets.QGroupBox):
    """Container padronizado em formato de cartão/caixa com borda e título estilizados."""

    def __init__(self, title: str, content_widget: QtWidgets.QWidget, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(title, parent)
        self.setObjectName("PanelCardBox")
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(content_widget)

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        border = theme.get_color("border", "#2e2e38")
        text_sec = theme.get_color("text_sec", "#9ca3af")

        self.setStyleSheet(f"""
            QGroupBox#PanelCardBox {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 8px;
                margin-top: 14px;
                font-weight: bold;
                font-size: 10px;
                color: {text_sec};
            }}
            QGroupBox#PanelCardBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                left: 10px;
                color: {text_sec};
            }}
        """)

