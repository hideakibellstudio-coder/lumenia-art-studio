"""CanvasToolBinding — aplica o ToolState ao canvas.

Único lugar que traduz "a ferramenta ativa mudou" e "as opções de uma
ferramenta mudaram" em ações no canvas: finalizar o texto aberto, trocar o
cursor, entrar/sair do modo transformar e entregar as opções ao controlador
certo (`ToolManager.apply_tool_settings`).

Substitui o `WorkspaceBrushMixin.select_tool` de antes de 2026-09-24, que
era chamado por quatro caminhos diferentes (painel, barra flutuante, janela,
atalhos), marcava a ferramenta em cada view à mão e precisava de uma guarda
de reentrância para não entrar em laço.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PySide6 import QtCore

from ui.infrastructure.i18n import tr
from ui.core.state import ToolState, options_key
from ui.core.tools import TOOL_META, get_tool_name

if TYPE_CHECKING:
    from .canvas.render_widget import RenderWidget


class CanvasToolBinding(QtCore.QObject):
    def __init__(
        self,
        tool_state: ToolState,
        canvas: "RenderWidget",
        notify: Callable[[str], None],
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._state = tool_state
        self._canvas = canvas
        self._notify = notify

        tool_state.activeToolChanged.connect(self._on_active_tool_changed)
        tool_state.optionsChanged.connect(self._on_options_changed)

        canvas.active_tool = tool_state.active_tool
        for tool_id in TOOL_META:
            options = tool_state.options(tool_id)
            if options:
                canvas.tool_mgr.apply_tool_settings(options_key(tool_id), options)

    def _on_active_tool_changed(self, tool: str, previous: str) -> None:
        canvas = self._canvas
        if previous == "text" and tool != "text":
            canvas.commit_text_overlay()
        canvas.active_tool = tool
        canvas.update_cursor_shape()

        # Retângulo e elipse dividem um controlador: ao alternar entre eles,
        # o controlador passa a usar as opções da ferramenta que ficou ativa.
        options = self._state.options(tool)
        if options:
            canvas.tool_mgr.apply_tool_settings(options_key(tool), options)

        if tool == "transform":
            canvas.start_transform_mode()
        elif canvas.transform_ctrl.active:
            canvas.commit_transform()

        name = get_tool_name(tool)
        if TOOL_META.get(tool, {}).get("implemented", False):
            self._notify(tr("status.tool_active", "Ferramenta ativa: {name}").format(name=name))
        else:
            self._notify(tr("status.tool_in_development", "Ferramenta '{name}' em desenvolvimento.").format(name=name))

    def _on_options_changed(self, key: str, options: dict) -> None:
        self._canvas.tool_mgr.apply_tool_settings(key, options)
