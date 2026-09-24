"""
WorkspaceActionsMixin — Ações de Visualização, Histórico e Limpeza do Canvas
=============================================================================
Isola os comandos de Desfazer/Refazer, Zoom/Pan, Reset View e Clear do WorkspaceContainer.
"""

from __future__ import annotations

import math
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget

logger = logging.getLogger("Workspace.Actions")

_HISTORY_ERROR_MESSAGES = {
    "scratch_read_failed": "scratch disk do histórico indisponível",
    "scratch_write_failed": "scratch disk do histórico não aceitou a gravação",
    "history_corrupt_snapshot": "snapshot do histórico corrompido",
    "history_invalid_snapshot": "snapshot do histórico inválido",
    "history_busy": "histórico ocupado por outra operação",
    "history_restore_failed": "falha ao restaurar o snapshot",
}


def _history_failure_message(action: str, error: str) -> str:
    detail = _HISTORY_ERROR_MESSAGES.get(error, error)
    return f"Falha ao {action}: {detail}. Documento preservado."


class WorkspaceActionsMixin:
    """Mixin responsável por operações de desfazer/refazer, zoom e limpeza de tela."""

    def undo(self) -> None:
        """Executa a operação de desfazer."""
        cw = self.canvas_widget
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend:
            from ui.core.document.manager import DocumentManager
            document = DocumentManager.instance().active_document()
            ok = document.history.undo(backend) if document else backend.undo()
            if ok:
                cw.update()
                self._on_status_notification("Desfazer executado com sucesso.")
                self._on_stroke_finished_sync_previews()
            else:
                error = backend.get_history_error()
                self._on_status_notification(_history_failure_message("desfazer", error) if error else "Nada a desfazer.")

    def redo(self) -> None:
        """Executa a operação de refazer."""
        cw = self.canvas_widget
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend:
            from ui.core.document.manager import DocumentManager
            document = DocumentManager.instance().active_document()
            ok = document.history.redo(backend) if document else backend.redo()
            if ok:
                cw.update()
                self._on_status_notification("Refazer executado com sucesso.")
                self._on_stroke_finished_sync_previews()
            else:
                error = backend.get_history_error()
                self._on_status_notification(_history_failure_message("refazer", error) if error else "Nada a refazer.")

    def reset_view(self) -> None:
        """Reposiciona o canvas para o centro e zoom 1:1."""
        if not self._dm.active_document():
            return
        self.canvas_widget.center_canvas()
        self.zoomChanged.emit(self.canvas_widget.zoom)
        self.canvas_widget.update()
        self._sync_navigator_to_canvas()

    def zoom_in(self) -> None:
        cw: "RenderWidget" = self.canvas_widget
        cw.zoom = min(50.0, cw.zoom * 1.2)
        if cw.input_adapter:
            rot_rad = math.radians(getattr(cw, "rotation", 0.0))
            cw.input_adapter.update_view(cw.zoom, cw.pan_x, cw.pan_y, rot_rad)
        self.zoomChanged.emit(cw.zoom)
        cw.update()

    def zoom_out(self) -> None:
        cw = self.canvas_widget
        cw.zoom = max(0.05, cw.zoom / 1.2)
        if cw.input_adapter:
            rot_rad = math.radians(getattr(cw, "rotation", 0.0))
            cw.input_adapter.update_view(cw.zoom, cw.pan_x, cw.pan_y, rot_rad)
        self.zoomChanged.emit(cw.zoom)
        cw.update()

    def clear_canvas(self) -> None:
        """Limpa o canvas (usado pelo MenuBar e ToolSidebar)."""
        if hasattr(self, "canvas_widget") and self.canvas_widget:
            self.canvas_widget.clear_canvas()
        elif self.canvas_widget.renderer:
            self.canvas_widget.renderer.clear_canvas()
            self.canvas_widget.update()

    def clear_selection(self) -> None:
        """Desmarca/limpa a seleção ativa do documento."""
        if hasattr(self.canvas_widget, "clear_selection"):
            self.canvas_widget.clear_selection()
        else:
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()
            if backend and hasattr(backend, "clear_selection"):
                backend.clear_selection()
            if hasattr(self.canvas_widget, "selection_ctrl"):
                self.canvas_widget.selection_ctrl.selection_timer.stop()
            self.canvas_widget.update()
        self._on_status_notification("Seleção cancelada.")

