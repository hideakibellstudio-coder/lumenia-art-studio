"""
CanvasCursorController — Controlador Modular do Cursor no Canvas (ARCcC)
========================================================================
Isola completamente o ciclo de vida do cursor da viewport:
  - Ativação do anel geométrico flutuante ESTRITAMENTE dentro dos limites da área em pixels do canvas/imagem.
  - Alternância imediata para a seta padrão do sistema (Qt.ArrowCursor) na área cinza do workspace fora do canvas.
  - Restauração determinística do cursor do sistema ao sair da viewport para docas, abas e menus.
  - Cálculo atômico de dirty rects / QRegion para repintura de ultra-alta taxa sem repaints de tela inteira.
  - Zero chamadas Win32 redundantes e cache de transformações para altíssima performance.

Dono de todo o estado do cursor (desde 2026-09-24):
  - `hover_ring_rect`: onde o anel foi invalidado pelo movimento sem traço;
  - `painted_ring_rect`: onde o anel foi de fato pintado por último
    (escrito pelo ViewportRenderer e pelo CanvasStrokePipeline).
Antes o segundo vivia no widget (`_last_rendered_cursor_rect`) e era escrito
por três módulos diferentes.
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
        self.over_canvas: bool = False
        self.mouse_pos: QtCore.QPointF = QtCore.QPointF(-1000.0, -1000.0)
        self.cursor_settings: dict = ToolCursorRenderer.get_cursor_settings()
        self._last_radius: float = 12.0
        self._current_shape: Optional[QtGui.QCursor | QtCore.Qt.CursorShape] = None
        self.hover_ring_rect: QtCore.QRect = QtCore.QRect()
        self.painted_ring_rect: QtCore.QRect = QtCore.QRect()
        self._cached_transform: Optional[QtGui.QTransform] = None
        self._cached_inv_transform: Optional[QtGui.QTransform] = None
        self._cached_inv_ok: bool = False

    def apply_settings(self, settings: dict) -> None:
        """Aplica preferências recém-salvas (diálogo de cursor) sem reler o disco."""
        self.cursor_settings = dict(settings)
        self.invalidate_cursor_cache()
        self.update_cursor_shape()

    def is_over_canvas(self, pos: QtCore.QPointF) -> bool:
        """Verifica se a posição do mouse na tela está dentro da área definida do canvas/imagem."""
        w = self.widget
        cw, ch = w.canvas_w, w.canvas_h
        if cw <= 0 or ch <= 0:
            return False

        t = w.canvas_transform()
        if self._cached_transform != t:
            self._cached_transform = t
            self._cached_inv_transform, self._cached_inv_ok = t.inverted()

        if not self._cached_inv_ok or self._cached_inv_transform is None:
            return False

        canvas_pt = self._cached_inv_transform.map(pos)
        return (0.0 <= canvas_pt.x() <= float(cw)) and (0.0 <= canvas_pt.y() <= float(ch))

    def invalidate_cursor_cache(self) -> None:
        """Invalida o cache de formato para forçar re-sincronização na próxima atualização."""
        self._current_shape = None

    def _set_widget_cursor(self, cursor: QtGui.QCursor | QtCore.Qt.CursorShape) -> None:
        """Aplica o cursor ao widget evitando chamadas redundantes ao Win32, conferindo sincronismo real."""
        if self._current_shape == cursor:
            actual = self.widget.cursor()
            if isinstance(cursor, QtCore.Qt.CursorShape) and actual.shape() == cursor:
                return
            elif isinstance(cursor, QtGui.QCursor) and actual == cursor:
                return
        self._current_shape = cursor
        self.widget.setCursor(cursor)

    def update_cursor_shape(self) -> None:
        """Define o formato do cursor do widget com base na ferramenta ativa, presença na viewport e preferências."""
        w = self.widget
        cw, ch = w.canvas_w, w.canvas_h

        # Fora da viewport ou sem documento: mostra SEMPRE a seta padrão
        if cw <= 0 or ch <= 0 or not self.cursor_in_viewport:
            self._set_widget_cursor(QtCore.Qt.ArrowCursor)
            return

        # Navegação de câmera ativa (Mão Livre / Panning)
        if w.is_panning:
            self._set_widget_cursor(QtCore.Qt.ClosedHandCursor)
            return
        if w.is_space_held:
            self._set_widget_cursor(QtCore.Qt.OpenHandCursor)
            return

        active_tool = w.active_tool
        mode = self.cursor_settings.get("mode", "ring_and_dot")
        ori = self.cursor_settings.get("orientation", "right")
        show_chev = self.cursor_settings.get("show_chevron", True)

        if active_tool in ("brush", "eraser", "smudge"):
            if mode == "system":
                self._set_widget_cursor(QtCore.Qt.ArrowCursor)
            elif mode == "blank":
                self._set_widget_cursor(QtCore.Qt.BlankCursor)
            elif mode in ("dot_only", "crosshair"):
                self._set_widget_cursor(QtCore.Qt.BlankCursor)
            elif mode == "ring_only":
                if show_chev:
                    dpr = self.widget.devicePixelRatioF()
                    self._set_widget_cursor(ToolCursorRenderer.create_precision_chevron_cursor(dpr, ori))
                else:
                    self._set_widget_cursor(QtCore.Qt.BlankCursor)
            elif mode == "chevron":
                dpr = self.widget.devicePixelRatioF()
                self._set_widget_cursor(ToolCursorRenderer.create_precision_chevron_cursor(dpr, ori))
            elif mode == "ring_and_dot":
                if show_chev:
                    dpr = self.widget.devicePixelRatioF()
                    self._set_widget_cursor(ToolCursorRenderer.create_precision_chevron_cursor(dpr, ori))
                else:
                    self._set_widget_cursor(QtCore.Qt.BlankCursor)
            else:
                dpr = self.widget.devicePixelRatioF()
                self._set_widget_cursor(ToolCursorRenderer.create_precision_chevron_cursor(dpr, ori))
        elif active_tool in ("eyedrop", "eyedropper", "bucket", "wand", "transform"):
            self._set_widget_cursor(ToolCursorRenderer.create_custom_cursor(active_tool))
        elif active_tool in ("lasso", "rect_select", "ellipse_select", "shapes") or active_tool.startswith("shape_"):
            self._set_widget_cursor(QtCore.Qt.CrossCursor)
        elif active_tool == "text":
            self._set_widget_cursor(QtCore.Qt.IBeamCursor)
        else:
            self._set_widget_cursor(QtCore.Qt.ArrowCursor)

    def handle_enter(self, event: QtCore.QEnterEvent) -> None:
        """Chamado quando o ponteiro entra na viewport."""
        self.cursor_in_viewport = True
        self.mouse_pos = event.position()
        self.over_canvas = self.is_over_canvas(self.mouse_pos)
        self.update_cursor_shape()

    def handle_leave(self, event: QtCore.QEvent) -> Optional[QtCore.QRect]:
        """
        Chamado quando o ponteiro sai da viewport.
        GARANTIA ARCcC: Restaura imediatamente a seta padrão e invalida o último anel.
        """
        self.cursor_in_viewport = False
        self.over_canvas = False
        self._set_widget_cursor(QtCore.Qt.ArrowCursor)

        dirty_rect = self.hover_ring_rect
        if dirty_rect.isEmpty() and self.mouse_pos.x() >= 0:
            w = self.widget
            dirty_rect = ToolCursorRenderer.get_cursor_rect(
                self.mouse_pos.x(), self.mouse_pos.y(),
                self._last_radius, w.zoom
            )
        self.mouse_pos = QtCore.QPointF(-1000.0, -1000.0)
        self.hover_ring_rect = QtCore.QRect()
        return dirty_rect if not dirty_rect.isEmpty() else None

    def sync_position(self, pos: QtCore.QPointF, brush_radius: float, zoom: float, recheck_canvas: bool = False) -> None:
        """Sincroniza atomicamente a posição durante traços sem disparar eventos de hover.

        Durante o traço o ponteiro é tratado como sobre o canvas; no fim do
        traço (`recheck_canvas=True`) a posição real é conferida.
        """
        self.mouse_pos = pos
        self.cursor_in_viewport = True
        self._last_radius = brush_radius
        self.over_canvas = self.is_over_canvas(pos) if recheck_canvas else True

    def handle_move(
        self,
        pos: QtCore.QPointF,
        brush_radius: float,
        zoom: float,
        is_drawing: bool
    ) -> Optional[QtCore.QRect | QtGui.QRegion]:
        """
        Atualiza a posição do cursor na viewport e emite dirty rect para re-renderização suave.
        Garante cálculo inteligente de dirty region sem repintar a tela inteira em saltos.
        """
        old_pos = self.mouse_pos
        self.mouse_pos = pos
        was_in_viewport = self.cursor_in_viewport
        self.cursor_in_viewport = True
        self._last_radius = brush_radius

        was_over = self.over_canvas
        self.over_canvas = self.is_over_canvas(pos)

        if not was_in_viewport:
            self.update_cursor_shape()

        w = self.widget
        if w.is_panning or w.is_space_held:
            return None

        active_tool = w.active_tool
        if active_tool in ("brush", "eraser", "smudge") and not is_drawing:
            r_new = ToolCursorRenderer.get_cursor_rect(self.mouse_pos.x(), self.mouse_pos.y(), brush_radius, zoom)

            # Se a posição anterior era inválida/fora da tela ou fora da viewport
            if old_pos.x() < -500.0 or old_pos.y() < -500.0 or not was_in_viewport:
                self.hover_ring_rect = r_new
                return r_new

            r_old = self.hover_ring_rect
            if r_old.isEmpty():
                r_old = ToolCursorRenderer.get_cursor_rect(old_pos.x(), old_pos.y(), brush_radius, zoom)
            self.hover_ring_rect = r_new

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
        """Renderiza o cursor flutuante personalizado (anel/ponto/mira) em toda a área visível da viewport."""
        w = self.widget
        if w.is_panning or w.is_space_held:
            return

        active_tool = w.active_tool
        if self.cursor_in_viewport and active_tool in ("brush", "eraser", "smudge"):
            ToolCursorRenderer.render_cursor(
                painter,
                self.mouse_pos.x(),
                self.mouse_pos.y(),
                brush_radius,
                zoom,
                is_drawing,
                self.cursor_settings,
                tool_id=active_tool,
            )
