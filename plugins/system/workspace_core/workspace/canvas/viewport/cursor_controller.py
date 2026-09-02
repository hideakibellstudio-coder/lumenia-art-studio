"""
CanvasCursorController — Controlador Modular do Cursor no Canvas (ARCcC)
========================================================================
Isola completamente o ciclo de vida do cursor da viewport:
  - Ativação do anel geométrico flutuante ESTRITAMENTE dentro dos limites da área em pixels do canvas/imagem.
  - Alternância imediata para a seta padrão do sistema (Qt.ArrowCursor) na área cinza do workspace fora do canvas.
  - Restauração determinística do cursor do sistema ao sair da viewport para docas, abas e menus.
  - Cálculo atômico de dirty rects para repintura de alta taxa (240+ FPS) com custo zero de CPU.
"""

from __future__ import annotations

import time
from typing import Optional, TYPE_CHECKING
from PySide6 import QtCore, QtGui, QtWidgets

from ..renderers.tool_cursor_renderer import ToolCursorRenderer

if TYPE_CHECKING:
    from ..render_widget import CanvasWidget


class CanvasCursorController:
    """Controlador atômico responsável pelo cursor do mouse e indicador geométrico de pincel."""

    def __init__(self, widget: "CanvasWidget"):
        self.widget = widget
        self.cursor_in_viewport: bool = False
        self._is_over_canvas: bool = False
        self.mouse_pos: QtCore.QPointF = QtCore.QPointF(-1000.0, -1000.0)
        self.cursor_settings: dict = ToolCursorRenderer.get_cursor_settings()
        self._last_radius: float = 12.0

    def reload_settings(self) -> None:
        """Recarrega as preferências do usuário para o cursor."""
        self.cursor_settings = ToolCursorRenderer.get_cursor_settings()
        self.update_cursor_shape()

    def is_over_canvas(self, pos: QtCore.QPointF) -> bool:
        """Verifica se a posição do mouse na tela está dentro da área definida do canvas/imagem."""
        from ui.core.document.manager import DocumentManager
        if not DocumentManager.instance().has_document():
            return False
        w = self.widget
        if not hasattr(w, "_get_canvas_transform"):
            return False
        t = w._get_canvas_transform()
        inv_t, ok = t.inverted()
        if not ok:
            return False
        canvas_pt = inv_t.map(pos)
        cw = getattr(w, "canvas_w", 0)
        ch = getattr(w, "canvas_h", 0)
        return (0.0 <= canvas_pt.x() <= float(cw)) and (0.0 <= canvas_pt.y() <= float(ch))

    def update_cursor_shape(self) -> None:
        """Define o formato do cursor do widget com base na ferramenta ativa, posição e preferências."""
        from ui.core.document.manager import DocumentManager
        w = self.widget

        if not DocumentManager.instance().has_document():
            w.unsetCursor()
            w.setCursor(QtCore.Qt.ArrowCursor)
            return

        # Se o cursor estiver fora dos limites do canvas (na área cinza do workspace), mostra SEMPRE a seta do sistema
        if not self._is_over_canvas:
            w.unsetCursor()
            w.setCursor(QtCore.Qt.ArrowCursor)
            return

        active_tool = getattr(w, "active_tool", "brush")
        mode = self.cursor_settings.get("mode", "ring_and_dot")

        if active_tool in ("brush", "eraser"):
            if mode == "system":
                w.unsetCursor()
                w.setCursor(QtCore.Qt.ArrowCursor)
            else:
                w.setCursor(QtCore.Qt.BlankCursor)
        elif active_tool in ("eyedropper", "bucket", "wand", "transform"):
            w.setCursor(ToolCursorRenderer.create_custom_cursor(active_tool))
        elif active_tool in ("lasso", "rect_select", "ellipse_select"):
            w.setCursor(QtCore.Qt.CrossCursor)
        else:
            w.unsetCursor()
            w.setCursor(QtCore.Qt.ArrowCursor)

    def handle_enter(self, event: QtCore.QEnterEvent) -> None:
        """Chamado quando o ponteiro entra na viewport."""
        self.cursor_in_viewport = True
        self.mouse_pos = event.position()
        self._is_over_canvas = self.is_over_canvas(self.mouse_pos)
        self.update_cursor_shape()

    def handle_leave(self, event: QtCore.QEvent) -> Optional[QtCore.QRect]:
        """
        Chamado quando o ponteiro sai da viewport.
        GARANTIA ARCcC: Restaura imediatamente e incondicionalmente a seta padrão do sistema operacional.
        """
        self.cursor_in_viewport = False
        self._is_over_canvas = False
        w = self.widget

        # 1. Restauração imediata do cursor do sistema operacional
        w.unsetCursor()
        w.setCursor(QtCore.Qt.ArrowCursor)

        # 2. Retorna a bounding box onde o anel estava para ser limpo do canvas
        dirty_rect = ToolCursorRenderer.get_cursor_rect(
            self.mouse_pos.x(), self.mouse_pos.y(),
            self._last_radius, getattr(w, "zoom", 1.0)
        )
        self.mouse_pos = QtCore.QPointF(-1000.0, -1000.0)
        return dirty_rect

    def handle_move(self, pos: QtCore.QPointF, brush_radius: float, zoom: float, is_drawing: bool) -> Optional[QtCore.QRect]:
        """
        Atualiza a posição do cursor e alterna determinística entre o anel do pincel (no canvas)
        e a seta do sistema operacional (fora do canvas).
        """
        old_pos = self.mouse_pos
        self.mouse_pos = pos
        self.cursor_in_viewport = True
        self._last_radius = brush_radius

        was_over = self._is_over_canvas
        now_over = self.is_over_canvas(pos)
        self._is_over_canvas = now_over

        w = self.widget
        # Transição de fronteira do canvas:
        if now_over != was_over:
            self.update_cursor_shape()

        from ui.core.document.manager import DocumentManager
        active_tool = getattr(w, "active_tool", "brush")
        if DocumentManager.instance().has_document() and active_tool in ("brush", "eraser") and not is_drawing:
            r_old = ToolCursorRenderer.get_cursor_rect(old_pos.x(), old_pos.y(), brush_radius, zoom)
            r_new = ToolCursorRenderer.get_cursor_rect(self.mouse_pos.x(), self.mouse_pos.y(), brush_radius, zoom)
            return r_old.united(r_new)
        return None

    def render(self, painter: QtGui.QPainter, brush_radius: float, zoom: float, is_drawing: bool) -> None:
        """Renderiza o cursor flutuante personalizado (anel/ponto/mira) SOMENTE se estiver sobre o canvas."""
        active_tool = getattr(self.widget, "active_tool", "brush")
        if self.cursor_in_viewport and self._is_over_canvas and active_tool in ("brush", "eraser"):
            ToolCursorRenderer.render_cursor(
                painter,
                self.mouse_pos.x(),
                self.mouse_pos.y(),
                brush_radius,
                zoom,
                is_drawing,
                self.cursor_settings
            )
