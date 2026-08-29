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
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(0)

        # 1. Roda de Cores Widget
        self.color_wheel = ColorWheelWidget(self, initial_color=initial_color)
        self.color_wheel.colorChanged.connect(self.colorChanged.emit)

        # 2. Moldura Padronizada CardBox (Clean Frame)
        card_box = PanelCardBox("", self.color_wheel, self)
        main_layout.addWidget(card_box)

    def set_color(self, color: QtGui.QColor) -> None:
        if hasattr(self.color_wheel, "set_color"):
            self.color_wheel.set_color(color)
