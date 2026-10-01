"""CanvasStrokePipeline — ciclo de vida do traço interativo e regiões sujas da tela.

Leva os eventos do ponteiro ao motor (com snap das guias), e decide o que
repintar: a área dos dabs novos unida ao anel do cursor antigo e novo, sem
repintar a tela inteira.

Colaborador com estado próprio (desde 2026-09-24): `last_draw_pos` (último
ponto no espaço do canvas) e `last_end_screen` (fim do último traço, usado
pela linha reta com Shift). Antes era uma classe de métodos estáticos que
recebia o widget e escrevia sete atributos privados dele; o anel do cursor
agora é do `CanvasCursorController` (`painted_ring_rect`).
"""

from __future__ import annotations

import math
import time
from typing import Any, Optional, Protocol, runtime_checkable

from PySide6 import QtCore, QtGui

from ui.core.engine.backend_protocols import StrokeProtocol

from ..renderers.tool_cursor_renderer import ToolCursorRenderer


@runtime_checkable
class StrokeCanvas(Protocol):
    """O que o traço interativo usa do canvas.

    Até 2026-09-25 este arquivo importava o `RenderWidget` da pasta mãe só
    para anotar tipo (o ciclo canvas ↔ viewport). Membro novo usado aqui entra
    neste contrato; `tests/test_canvas_contracts.py` confere que o
    `RenderWidget` o cumpre.
    """
    drawing: bool
    zoom: float
    current_brush_radius: float
    backend: Optional[StrokeProtocol]
    cursor_ctrl: Any
    geometry_ctrl: Any
    strokeStarted: Any
    strokeFinished: Any

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> Any: ...
    def canvas_transform(self) -> QtGui.QTransform: ...
    def update(self, *args: Any) -> None: ...

_MIN_PRESSURE = 0.02
_DIRTY_MARGIN_PX = 6
# Sem dabs novos, o anel só é redesenhado a cada 8 ms ou 2 px de movimento.
_RING_REFRESH_S = 0.008
_RING_REFRESH_PX = 2.0


class CanvasStrokePipeline:
    def __init__(self, widget: StrokeCanvas) -> None:
        self._w = widget
        self.last_draw_pos: Optional[tuple[float, float]] = None
        self.last_end_screen: Optional[QtCore.QPointF] = None
        self._last_ring_refresh_time = 0.0
        self._last_ring_refresh_pos: Optional[tuple[float, float]] = None

    def start(self, screen_x: float, screen_y: float, pressure: float, timestamp: float = 0.0,
              tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0) -> None:
        """Começa um traço: snap da origem e envio ao motor."""
        w = self._w
        w.strokeStarted.emit()
        w.cursor_ctrl.painted_ring_rect = QtCore.QRect()
        backend = w.backend
        if backend is None:
            return
        w.drawing = True
        safe_pressure = max(_MIN_PRESSURE, pressure)
        evt = w.to_canvas(screen_x, screen_y, safe_pressure, timestamp)
        w.geometry_ctrl.start_stroke_snap((evt.x, evt.y))
        cur_x, cur_y = w.geometry_ctrl.snap_point(evt.x, evt.y, w.zoom)
        self.last_draw_pos = (cur_x, cur_y)
        backend.start_stroke(cur_x, cur_y, safe_pressure, timestamp, tilt_x, tilt_y, twist)
        w.update()

    def paint(self, screen_x: float, screen_y: float, pressure: float, timestamp: float = 0.0,
              tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0) -> None:
        """Alimenta o motor e repinta só a união (dabs novos ∪ anel antigo ∪ anel novo)."""
        w = self._w
        if not w.drawing:
            return
        backend = w.backend
        if backend is None:
            return
        cursor = w.cursor_ctrl
        cursor.sync_position(QtCore.QPointF(screen_x, screen_y), w.current_brush_radius, w.zoom)
        safe_p = max(_MIN_PRESSURE, pressure)
        evt = w.to_canvas(screen_x, screen_y, safe_p, timestamp)
        cur_x, cur_y = w.geometry_ctrl.snap_point(evt.x, evt.y, w.zoom)
        res = backend.paint_stroke(cur_x, cur_y, safe_p, timestamp, tilt_x, tilt_y, twist)
        self.last_draw_pos = (cur_x, cur_y)

        if w.geometry_ctrl.sym_state.get("mode", "none") != "none":
            w.update()  # simetria espalha dabs pela tela toda
            return

        has_rendered_dabs = bool(res and len(res) >= 6 and res[2] > 0 and res[3] > 0)
        cursor_visible = cursor.cursor_in_viewport and not cursor.cursor_settings.get("hide_on_stroke", False)
        new_ring = (
            ToolCursorRenderer.get_cursor_rect(screen_x, screen_y, w.current_brush_radius, w.zoom)
            if cursor_visible else QtCore.QRect()
        )
        old_ring = cursor.painted_ring_rect

        if has_rendered_dabs:
            m = _DIRTY_MARGIN_PX
            dirty = w.canvas_transform().mapRect(QtCore.QRectF(res[0], res[1], res[2], res[3])).toAlignedRect().adjusted(-m, -m, m, m)
            if not old_ring.isEmpty():
                dirty = dirty.united(old_ring)
            if cursor_visible:
                dirty = dirty.united(new_ring)
            w.update(dirty)
            self._remember_ring(cursor, new_ring, screen_x, screen_y, time.perf_counter())
            return

        now = time.perf_counter()
        last_pos = self._last_ring_refresh_pos or (screen_x, screen_y)
        moved = math.hypot(screen_x - last_pos[0], screen_y - last_pos[1])
        if (now - self._last_ring_refresh_time) >= _RING_REFRESH_S or moved >= _RING_REFRESH_PX:
            if cursor_visible:
                w.update(new_ring if old_ring.isEmpty() else new_ring.united(old_ring))
            elif not old_ring.isEmpty():
                w.update(old_ring)
            self._remember_ring(cursor, new_ring, screen_x, screen_y, now)

    def end(self, screen_x: float | None = None, screen_y: float | None = None) -> None:
        """Termina o traço e repinta a área final (inclusive o toque isolado sem arrasto)."""
        w = self._w
        w.geometry_ctrl.mouse_release()
        backend = w.backend
        if not w.drawing or backend is None:
            w.drawing = False
            w.strokeFinished.emit()
            return

        cursor = w.cursor_ctrl
        if screen_x is not None and screen_y is not None:
            evt = w.to_canvas(screen_x, screen_y, 0.0, 0.0)
            res = backend.end_stroke(evt.x, evt.y)
            end_pos = QtCore.QPointF(screen_x, screen_y)
        else:
            res = backend.end_stroke()
            end_pos = cursor.mouse_pos

        w.drawing = False
        self.last_end_screen = end_pos
        cursor.sync_position(end_pos, w.current_brush_radius, w.zoom, recheck_canvas=True)

        if res and len(res) >= 4 and res[2] > 0 and res[3] > 0:
            dirty = w.canvas_transform().mapRect(QtCore.QRectF(res[0], res[1], res[2], res[3])).toAlignedRect()
        else:
            # Toque isolado (ou motor sem retângulo de catch-up): invalida a
            # área analítica do dab sob o ponto final, senão a marca não aparece.
            rad = w.current_brush_radius * w.zoom + _DIRTY_MARGIN_PX
            dirty = QtCore.QRectF(end_pos.x() - rad, end_pos.y() - rad, rad * 2.0, rad * 2.0).toAlignedRect()

        new_ring = ToolCursorRenderer.get_cursor_rect(end_pos.x(), end_pos.y(), w.current_brush_radius, w.zoom)
        if not cursor.painted_ring_rect.isEmpty():
            dirty = dirty.united(cursor.painted_ring_rect) if not dirty.isEmpty() else cursor.painted_ring_rect
        dirty = dirty.united(new_ring) if not dirty.isEmpty() else new_ring

        cursor.painted_ring_rect = new_ring
        cursor.hover_ring_rect = new_ring
        if not dirty.isEmpty():
            w.update(dirty)
        w.strokeFinished.emit()

    def _remember_ring(self, cursor, ring: QtCore.QRect, x: float, y: float, when: float) -> None:
        cursor.painted_ring_rect = ring
        self._last_ring_refresh_time = when
        self._last_ring_refresh_pos = (x, y)
