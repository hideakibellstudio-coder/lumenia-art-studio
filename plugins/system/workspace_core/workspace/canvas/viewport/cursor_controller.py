"""
CanvasCursorController — Controlador Modular do Cursor no Canvas (ARCcC)
========================================================================
Isola completamente o ciclo de vida do cursor da viewport:
  - Ativação do anel geométrico flutuante ESTRITAMENTE dentro dos limites da área em pixels do canvas/imagem.
  - Alternância imediata para a seta padrão do sistema (Qt.ArrowCursor) na área cinza do workspace fora do canvas.
  - Restauração determinística do cursor do sistema ao sair da viewport para docas, abas e menus.
  - Cálculo atômico de dirty rects / QRegion para repintura de ultra-alta taxa sem repaints de tela inteira.
  - Zero chamadas Win32 redundantes e cache de transformações para altíssima performance.
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
        self._current_shape: Optional[QtGui.QCursor | QtCore.Qt.CursorShape] = None
        self._last_cursor_rect: QtCore.QRect = QtCore.QRect()
        self._cached_transform: Optional[QtGui.QTransform] = None
        self._cached_inv_transform: Optional[QtGui.QTransform] = None
        self._cached_inv_ok: bool = False

    def reload_settings(self) -> None:
        """Recarrega as preferências do usuário para o cursor."""
        self.cursor_settings = ToolCursorRenderer.get_cursor_settings()
        self.update_cursor_shape()

    def is_over_canvas(self, pos: QtCore.QPointF) -> bool:
        """Verifica se a posição do mouse na tela está dentro da área definida do canvas/imagem."""
        w = self.widget
        cw = getattr(w, "canvas_w", 0)
        ch = getattr(w, "canvas_h", 0)
        if cw <= 0 or ch <= 0:
            return False

        if not hasattr(w, "_get_canvas_transform"):
            return False

        t = w._get_canvas_transform()
        if self._cached_transform != t:
            self._cached_transform = t
            self._cached_inv_transform, self._cached_inv_ok = t.inverted()

        if not self._cached_inv_ok or self._cached_inv_transform is None:
            return False

        canvas_pt = self._cached_inv_transform.map(pos)
        return (0.0 <= canvas_pt.x() <= float(cw)) and (0.0 <= canvas_pt.y() <= float(ch))

    def _set_widget_cursor(self, cursor: QtGui.QCursor | QtCore.Qt.CursorShape) -> None:
        """Aplica o cursor ao widget evitando chamadas redundantes ao Win32."""
        if self._current_shape == cursor:
            return
        self._current_shape = cursor
        self.widget.setCursor(cursor)

    def update_cursor_shape(self) -> None:
        """Define o formato do cursor do widget com base na ferramenta ativa, posição e preferências."""
        w = self.widget
        cw = getattr(w, "canvas_w", 0)
        ch = getattr(w, "canvas_h", 0)

        # Fora do canvas ou sem documento: mostra SEMPRE a seta padrão
        if cw <= 0 or ch <= 0 or not self._is_over_canvas:
            self._set_widget_cursor(QtCore.Qt.ArrowCursor)
            return

        active_tool = getattr(w, "active_tool", "brush")
        mode = self.cursor_settings.get("mode", "ring_and_dot")

        if active_tool in ("brush", "eraser"):
            if mode == "system":
                self._set_widget_cursor(QtCore.Qt.ArrowCursor)
            else:
                self._set_widget_cursor(QtCore.Qt.BlankCursor)
        elif active_tool in ("eyedropper", "bucket", "wand", "transform"):
            self._set_widget_cursor(ToolCursorRenderer.create_custom_cursor(active_tool))
        elif active_tool in ("lasso", "rect_select", "ellipse_select"):
            self._set_widget_cursor(QtCore.Qt.CrossCursor)
        else:
            self._set_widget_cursor(QtCore.Qt.ArrowCursor)

    def handle_enter(self, event: QtCore.QEnterEvent) -> None:
        """Chamado quando o ponteiro entra na viewport."""
        self.cursor_in_viewport = True
        self.mouse_pos = event.position()
        self._is_over_canvas = self.is_over_canvas(self.mouse_pos)
        self.update_cursor_shape()

    def handle_leave(self, event: QtCore.QEvent) -> Optional[QtCore.QRect]:
        """
        Chamado quando o ponteiro sai da viewport.
        GARANTIA ARCcC: Restaura imediatamente a seta padrão e invalida o último anel.
        """
        self.cursor_in_viewport = False
        self._is_over_canvas = False
        self._set_widget_cursor(QtCore.Qt.ArrowCursor)

        dirty_rect = self._last_cursor_rect
        if dirty_rect.isEmpty() and self.mouse_pos.x() >= 0:
            w = self.widget
            dirty_rect = ToolCursorRenderer.get_cursor_rect(
                self.mouse_pos.x(), self.mouse_pos.y(),
                self._last_radius, getattr(w, "zoom", 1.0)
            )
        self.mouse_pos = QtCore.QPointF(-1000.0, -1000.0)
        self._last_cursor_rect = QtCore.QRect()
        return dirty_rect if not dirty_rect.isEmpty() else None

    def sync_position(self, pos: QtCore.QPointF, brush_radius: float, zoom: float) -> None:
        """Sincroniza atomicamente a posição durante traços sem disparar eventos de hover."""
        self.mouse_pos = pos
        self.cursor_in_viewport = True
        self._last_radius = brush_radius
        self._is_over_canvas = True

    def handle_move(
        self,
        pos: QtCore.QPointF,
        brush_radius: float,
        zoom: float,
        is_drawing: bool
    ) -> Optional[QtCore.QRect | QtGui.QRegion]:
        """
        Atualiza a posição do cursor e alterna determinística entre o anel do pincel (no canvas)
        e a seta do sistema operacional (fora do canvas).
        Garante cálculo inteligente de dirty region sem repintar a tela inteira em saltos.
        """
        old_pos = self.mouse_pos
        self.mouse_pos = pos
        self.cursor_in_viewport = True
        self._last_radius = brush_radius

        was_over = self._is_over_canvas
        now_over = self.is_over_canvas(pos)
        self._is_over_canvas = now_over

        if now_over != was_over:
            self.update_cursor_shape()

        w = self.widget
        active_tool = getattr(w, "active_tool", "brush")
        if active_tool in ("brush", "eraser") and not is_drawing:
            # Se não está nem estava sobre o canvas, não há anel geométrico a redesenhar
            if not now_over and not was_over:
                return None

            r_new = ToolCursorRenderer.get_cursor_rect(self.mouse_pos.x(), self.mouse_pos.y(), brush_radius, zoom)

            # Se a posição anterior era inválida/fora da tela ou fora do canvas
            if old_pos.x() < -500.0 or old_pos.y() < -500.0 or not was_over:
                self._last_cursor_rect = r_new
                return r_new

            r_old = self._last_cursor_rect
            if r_old.isEmpty():
                r_old = ToolCursorRenderer.get_cursor_rect(old_pos.x(), old_pos.y(), brush_radius, zoom)
            self._last_cursor_rect = r_new

            # Se o cursor se moveu uma distância muito grande (ex: salto após final de traço ou teletransporte),
            # união em bounding box único cobriria a tela inteira!
            # Usar QRegion evita repintar o intervalo vazio entre as posições.
            dx = pos.x() - old_pos.x()
            dy = pos.y() - old_pos.y()
            span_thresh = (brush_radius * zoom * 2.0 + 32.0)
            if (dx * dx + dy * dy) > (span_thresh * span_thresh):
                region = QtGui.QRegion(r_old)
                region = region.united(QtGui.QRegion(r_new))
                return region

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
