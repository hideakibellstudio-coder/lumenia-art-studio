"""ViewportRenderer — pinta o canvas: papel, pixels do motor, overlays e cursor.

Colaborador com estado próprio (desde 2026-09-24): as medições da última
pintura (`stats`, lidas pela telemetria) e o pincel xadrez do fundo
transparente. Antes era uma classe de métodos estáticos que escrevia sete
atributos privados do widget (`_last_qt_paint_total_ms`, ...).
"""

from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from PySide6 import QtCore, QtGui

from ui.infrastructure.theme.manager import ThemeManager
from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry

from ..renderers.overlay_renderer import OverlayRenderer
from ..renderers.geometry_overlay_renderer import GeometryOverlayRenderer
from ..renderers.canvas_background_renderer import CanvasBackgroundRenderer
from ..renderers.tool_cursor_renderer import ToolCursorRenderer



@runtime_checkable
class ViewportCanvas(Protocol):
    """O que a pintura da tela usa do canvas.

    Até 2026-09-25 este arquivo importava o `RenderWidget` da pasta mãe só
    para anotar tipo (o ciclo canvas ↔ viewport). Membro novo usado aqui entra
    neste contrato; `tests/test_canvas_contracts.py` confere que o
    `RenderWidget` o cumpre.
    """
    active_tool: str
    drawing: bool
    zoom: float
    canvas_w: int
    canvas_h: int
    current_brush_radius: float
    paper_color: QtGui.QColor
    paper_visible: bool
    cursor_ctrl: Any
    eyedrop_ctrl: Any
    geometry_ctrl: Any
    selection_ctrl: Any
    shape_ctrl: Any
    transform_ctrl: Any

    def canvas_transform(self) -> QtGui.QTransform: ...
    def rect(self) -> QtCore.QRect: ...


@dataclass
class ViewportPaintStats:
    """Medições da última pintura, expostas pela telemetria da viewport."""

    paint_total_ms: float = 0.0
    draw_image_ms: float = 0.0
    cursor_ms: float = 0.0
    fps: float = 0.0
    dirty_rect: QtCore.QRect = field(default_factory=QtCore.QRect)
    timestamps: collections.deque = field(default_factory=lambda: collections.deque(maxlen=60))

    def as_telemetry(self, gpu_accelerated: bool) -> dict:
        """Dicionário lido pelo cockpit de telemetria (chaves `qt_*`)."""
        return {
            "is_gpu_accelerated": gpu_accelerated,
            "renderer_type": "OpenGL" if gpu_accelerated else "Software Raster",
            "qt_paint_total_ms": self.paint_total_ms,
            "qt_draw_image_ms": self.draw_image_ms,
            "qt_cursor_ms": self.cursor_ms,
            "qt_fps": self.fps,
            "qt_dirty_w": self.dirty_rect.width(),
            "qt_dirty_h": self.dirty_rect.height(),
            "qt_dirty_area": self.dirty_rect.width() * self.dirty_rect.height(),
        }


class ViewportRenderer:
    """Orquestrador de renderização da viewport (QOpenGLWidget / QWidget)."""

    def __init__(self, widget: ViewportCanvas) -> None:
        self._w = widget
        self.stats = ViewportPaintStats()
        self._checker_brush = CanvasBackgroundRenderer.create_checker_brush()

    def render(self, event: QtGui.QPaintEvent) -> None:
        widget = self._w
        stats = self.stats
        t_paint_start = time.perf_counter()

        painter = QtGui.QPainter(widget)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        painter.fillRect(event.rect(), QtGui.QColor(128, 128, 128))

        active_doc = DocumentManager.instance().active_document()
        if active_doc is None:
            tm = ThemeManager.instance()
            painter.setPen(QtGui.QColor(tm.get_color("text_sec", "#9ca3af")))
            painter.setFont(QtGui.QFont("Segoe UI", 12, QtGui.QFont.Bold))
            from ui.infrastructure.i18n import tr
            title = tr("workspace.no_document", "Nenhum Documento Aberto")
            hint = tr("workspace.no_document_hint", "Pressione Ctrl+N ou Arquivo > Novo Documento")
            painter.drawText(widget.rect(), QtCore.Qt.AlignCenter, f"{title}\n\n{hint}")
            painter.end()
            return

        widget.canvas_w, widget.canvas_h = active_doc.width, active_doc.height
        backend = EngineRegistry.instance().get_backend()
        t = widget.canvas_transform()
        canvas_rect = QtCore.QRectF(0, 0, widget.canvas_w, widget.canvas_h)

        # Mapeia a região dirty do evento para o canvas local com alinhamento inteiro
        inv_t, ok = t.inverted()
        if ok:
            dirty_canvas = inv_t.mapRect(QtCore.QRectF(event.rect())).toAlignedRect().intersected(canvas_rect.toRect())
        else:
            dirty_canvas = canvas_rect.toRect()

        try:
            painter.save()
            try:
                painter.setTransform(t, combine=False)

                if not dirty_canvas.isEmpty():
                    painter.fillRect(dirty_canvas, widget.paper_color if widget.paper_visible else self._checker_brush)

                    if backend:
                        qimg, lod_scale = backend.get_qimage_lod(widget.zoom)
                        if qimg and not qimg.isNull():
                            t_blit_0 = time.perf_counter()
                            if abs(lod_scale - 1.0) < 1e-4:
                                painter.drawImage(dirty_canvas, qimg, dirty_canvas)
                            else:
                                src_x = int(dirty_canvas.x() * lod_scale)
                                src_y = int(dirty_canvas.y() * lod_scale)
                                src_w = max(1, int(dirty_canvas.width() * lod_scale))
                                src_h = max(1, int(dirty_canvas.height() * lod_scale))
                                lod_src = QtCore.QRect(src_x, src_y, src_w, src_h).intersected(
                                    QtCore.QRect(0, 0, qimg.width(), qimg.height())
                                )
                                painter.drawImage(dirty_canvas, qimg, lod_src)
                            stats.draw_image_ms = (time.perf_counter() - t_blit_0) * 1000.0

                if backend and backend.has_selection():
                    OverlayRenderer.render_selection_overlay(
                        painter, backend, widget.zoom,
                        widget.selection_ctrl.selection_dash_offset,
                        widget.canvas_w, widget.canvas_h
                    )

                if widget.selection_ctrl.drag_active or widget.selection_ctrl.lasso_is_drawing or (widget.active_tool == "lasso" and len(widget.selection_ctrl.lasso_points) > 0):
                    OverlayRenderer.render_selection_drag_preview(painter, widget, widget.zoom)

                if widget.transform_ctrl.active:
                    OverlayRenderer.render_transform_overlay(painter, widget.transform_ctrl, widget.zoom)

                if widget.shape_ctrl.drag_active:
                    OverlayRenderer.render_shape_drag_preview(painter, widget.shape_ctrl)

                if not (widget.drawing and widget.geometry_ctrl.guide_state.get("hidden", False)):
                    GeometryOverlayRenderer.render_symmetry(painter, widget.geometry_ctrl.sym_state, widget.zoom)
                    GeometryOverlayRenderer.render_guides(painter, widget.geometry_ctrl, widget.zoom)
            finally:
                painter.restore()

            if widget.eyedrop_ctrl.active and widget.eyedrop_ctrl.settings.get("show_loupe", True):
                OverlayRenderer.render_color_loupe(
                    painter, widget.eyedrop_ctrl.pos, widget, backend,
                    widget.eyedrop_ctrl.current_color, widget.eyedrop_ctrl.old_color
                )

            t_cur_0 = time.perf_counter()
            cursor = widget.cursor_ctrl
            should_hide = widget.drawing and cursor.cursor_settings.get("hide_on_stroke", False)
            if cursor.cursor_in_viewport and not should_hide and widget.active_tool in ("brush", "eraser", "smudge"):
                cur_rect = ToolCursorRenderer.get_cursor_rect(
                    cursor.mouse_pos.x(), cursor.mouse_pos.y(), widget.current_brush_radius, widget.zoom
                )
                if event.rect().intersects(cur_rect) or event.region().intersects(cur_rect):
                    cursor.render(painter, widget.current_brush_radius, widget.zoom, widget.drawing)
                    cursor.painted_ring_rect = cur_rect
            else:
                cursor.render(painter, widget.current_brush_radius, widget.zoom, widget.drawing)
                cursor.painted_ring_rect = QtCore.QRect()
            stats.cursor_ms = (time.perf_counter() - t_cur_0) * 1000.0
        finally:
            painter.end()
            t_paint_end = time.perf_counter()
            stats.paint_total_ms = (t_paint_end - t_paint_start) * 1000.0
            stats.dirty_rect = event.rect()
            stats.timestamps.append(t_paint_end)
            if len(stats.timestamps) >= 2:
                dt = stats.timestamps[-1] - stats.timestamps[0]
                if dt > 0.001:
                    stats.fps = (len(stats.timestamps) - 1) / dt

    @staticmethod
    def get_canvas_image(widget: ViewportCanvas, apply_proofing: bool = True) -> QtGui.QImage | None:
        composite = QtGui.QImage(widget.canvas_w, widget.canvas_h, QtGui.QImage.Format_RGBA8888)
        composite.fill(widget.paper_color if widget.paper_visible else QtCore.Qt.transparent)

        p = QtGui.QPainter(composite)
        backend = EngineRegistry.instance().get_backend()
        if backend:
            qimg = backend.get_qimage()
            if qimg and not qimg.isNull():
                p.drawImage(0, 0, qimg)
        p.end()
        return composite
