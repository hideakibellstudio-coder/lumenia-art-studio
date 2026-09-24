"""Regras entre estados: o que muda num estado por causa de outro, ou do motor.

Duas regras que antes eram reimplementadas por cada tela que as conhecia:

- `ShapeColorLink`: as formas desenham com a cor do pincel. O contorno passa
  a ser a cor nova; o fundo recebe a cor nova com a opacidade de fundo que já
  tinha. Até 2026-09-24 isto existia três vezes (canvas, barra secundária e
  painel de pincel), e o canvas zerava a transparência do fundo que as outras
  duas preservavam.
- `ToolEngineSync`: as opções do Smudge são parâmetros do perfil nativo do
  pincel. Antes eram escritas no motor pelo widget da barra secundária.
"""
from __future__ import annotations

from PySide6 import QtCore, QtGui

from .brush_engine_sync import BackendProvider
from .brush_state import BrushState
from .tool_state import ToolState

# Opções da ferramenta "smudge" que são parâmetros do grupo "smudge" do motor.
_SMUDGE_ENGINE_PARAMS = ("smudge_stretch", "color_pickup", "mix_ratio")


class ShapeColorLink(QtCore.QObject):
    """Cor do pincel → cores das formas (contorno e fundo)."""

    def __init__(self, brush: BrushState, tools: ToolState, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._tools = tools
        brush.colorChanged.connect(self._follow)
        self._follow(brush.color)

    def _follow(self, color: QtGui.QColor) -> None:
        fill_alpha = self._tools.options("shapes")["fill_color"].alpha()
        fill = QtGui.QColor(color)
        fill.setAlpha(fill_alpha)
        self._tools.update_options("shapes", {"stroke_color": QtGui.QColor(color), "fill_color": fill})


class ToolEngineSync(QtCore.QObject):
    """Opções de ferramenta que o motor consome → backend ativo."""

    def __init__(self, tools: ToolState, backend_provider: BackendProvider, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._backend_provider = backend_provider
        tools.optionsChanged.connect(self._push)

    def _push(self, key: str, options: dict) -> None:
        if key != "smudge":
            return
        backend = self._backend_provider()
        if backend is None:
            return
        for param in _SMUDGE_ENGINE_PARAMS:
            backend.set_brush_param("smudge", param, options[param])
