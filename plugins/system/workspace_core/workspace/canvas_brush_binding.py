"""CanvasBrushBinding — mostra o BrushState no canvas.

O canvas usa três coisas do pincel para desenhar a própria interface: a cor
(balde, conta-gotas), o tamanho (anel do cursor) e a pressão manual
(traço com mouse). Esta classe é o único lugar que copia esses valores do
estado para o canvas, e o único que devolve ao estado a cor capturada pelo
conta-gotas.

É um colaborador com estado próprio (não um mixin): recebe tudo o que usa pelo
construtor e não lê nada do WorkspaceContainer.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui

from ui.core.state import BrushParam, BrushState

if TYPE_CHECKING:
    from .canvas.render_widget import RenderWidget


class CanvasBrushBinding(QtCore.QObject):
    def __init__(
        self,
        brush_state: BrushState,
        canvas: "RenderWidget",
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._canvas = canvas

        brush_state.colorChanged.connect(self._show_color)
        brush_state.paramChanged.connect(self._show_param)
        canvas.colorPicked.connect(brush_state.set_color)

        self._show_color(brush_state.color)
        for param in (BrushParam.SIZE, BrushParam.PRESSURE):
            self._show_param(param, brush_state.value(param))

    def _show_color(self, color: QtGui.QColor) -> None:
        # As cores das formas seguem o pincel pelo ShapeColorLink (ui/core/state).
        self._canvas.active_color = color
        self._canvas.update()

    def _show_param(self, param: BrushParam, value) -> None:
        if param is BrushParam.SIZE:
            self._canvas.brush_size = float(value)
        elif param is BrushParam.PRESSURE:
            self._canvas.manual_pressure = float(value)
        self._canvas.update()
