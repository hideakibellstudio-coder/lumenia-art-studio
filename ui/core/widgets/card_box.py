"""
PanelCardBox — Caixa/Cartão Padronizado de Design System para Painéis V2
========================================================================
Fornece uma moldura de cartão ("box") elegante, padronizada e responsiva
para envolver os painéis dentro das gavetas do Lumenia V2 sem labels de topo.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets
from ui.infrastructure.theme.manager import ThemeManager


class PanelCardBox(QtWidgets.QFrame):
    """Container padronizado em formato de cartão com bordas arredondadas e estilo clean."""

    def __init__(
        self,
        title: str = "",
        content_widget: QtWidgets.QWidget | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PanelCardBox")
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        if content_widget:
            layout.addWidget(content_widget, 1)

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_card = theme.get_color("bg_card", "#221c33")
        border  = theme.get_color("border", "#2e2e38")

        self.setStyleSheet(f"""
            QFrame#PanelCardBox {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 8px;
                margin: 4px 6px;
            }}
        """)
