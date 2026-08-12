"""
ColorWheelPanel — Painel Isolado da Roda de Cores
=================================================
Painel individual contendo a Roda de Cores HSL e amostradores de cores recentes,
envolvido na moldura padronizada PanelCardBox.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets
from .color_wheel import ColorWheelWidget
from ui.core.widgets.card_box import PanelCardBox


class ColorWheelPanel(QtWidgets.QWidget):
    """Painel isolado contendo a Roda de Cores e Paletas Recentes."""

    colorChanged = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent: QtWidgets.QWidget | None = None, initial_color: QtGui.QColor | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ColorWheelPanel")

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        # 1. Roda de Cores Widget
        self.color_wheel = ColorWheelWidget(self, initial_color=initial_color)
        self.color_wheel.colorChanged.connect(self.colorChanged.emit)

        # 2. Moldura Padronizada CardBox
        card_box = PanelCardBox("🎨 Roda de Cores", self.color_wheel, self)

        # 3. Scroll Area para acomodar responsivamente
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        scroll_content = QtWidgets.QWidget()
        sc_layout = QtWidgets.QVBoxLayout(scroll_content)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.addWidget(card_box)
        sc_layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def set_color(self, color: QtGui.QColor) -> None:
        if hasattr(self.color_wheel, "set_color"):
            self.color_wheel.set_color(color)
