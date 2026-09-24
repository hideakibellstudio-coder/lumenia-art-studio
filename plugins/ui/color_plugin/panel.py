"""
ColorWheelPanel — Painel Isolado da Roda de Cores
=================================================
Roda de cores HSL, harmonias e cores recentes, na moldura padrão PanelCardBox.

Contrato (desde 2026-09-24): é uma view do `BrushState`. A cor escolhida na
roda vai para `BrushState.set_color`; qualquer mudança de cor vinda de outro
lugar (conta-gotas, troca de documento) chega pelo sinal `colorChanged` do
estado. O painel não conhece o workspace nem o motor.
"""

from __future__ import annotations

from PySide6 import QtGui, QtWidgets

from ui.core.state import BrushState
from ui.core.widgets.card_box import PanelCardBox
from ui.core.widgets.color_picker.color_wheel import ColorWheelWidget


class ColorWheelPanel(QtWidgets.QWidget):
    """Painel isolado contendo a Roda de Cores e Paletas Recentes."""

    def __init__(self, brush_state: BrushState, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ColorWheelPanel")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        self._state = brush_state

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(0)

        self.color_wheel = ColorWheelWidget(self, initial_color=brush_state.color)
        self.color_wheel.colorChanged.connect(brush_state.set_color)
        brush_state.colorChanged.connect(self._show_color)

        card_box = PanelCardBox("", self.color_wheel, self)
        main_layout.addWidget(card_box)

    def _show_color(self, color: QtGui.QColor) -> None:
        self.color_wheel.set_color(color)
