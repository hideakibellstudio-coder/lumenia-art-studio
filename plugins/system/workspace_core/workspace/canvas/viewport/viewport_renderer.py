"""ViewportRenderer — Orquestrador de Pintura Acelerada e Overlays do Canvas."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from PySide6 import QtCore, QtGui

from ui.core.theme.manager import ThemeManager
from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry

from ..renderers.overlay_renderer import OverlayRenderer
from ..renderers.geometry_overlay_renderer import GeometryOverlayRenderer
from ..renderers.tool_cursor_renderer import ToolCursorRenderer

if TYPE_CHECKING:
    from ..render_widget import RenderWidget


class ViewportRenderer:
    """Orquestrador desacoplado de renderização de Viewport (QOpenGLWidget / QWidget)."""

    @staticmethod
    def render(widget: RenderWidget, event: QtGui.QPaintEvent) -> None:
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
            from ui.core.i18n import tr
            title = tr("workspace.no_document", "Nenhum Documento Aberto")
            hint = tr("workspace.no_document_hint", "Pressione Ctrl+N ou Arquivo > Novo Documento")
            painter.drawText(widget.rect(), QtCore.Qt.AlignCenter, f"{title}\n\n{hint}")
            painter.end()
            return

        widget.canvas_w, widget.canvas_h = active_doc.width, active_doc.height
        backend = EngineRegistry.instance().get_backend()
        t = widget._get_canvas_transform()
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
                    painter.fillRect(dirty_canvas, widget.paper_color if widget.paper_visible else widget._checker_brush)

                    if backend:
                        qimg, lod_scale = (
                            backend.get_qimage_lod(widget.zoom)
                            if hasattr(backend, "get_qimage_lod")
                            else (backend.get_qimage() if hasattr(backend, "get_qimage") else (None, 1.0))
                        )
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
                            widget._last_qt_draw_image_ms = (time.perf_counter() - t_blit_0) * 1000.0

                if backend and hasattr(backend, "has_selection") and backend.has_selection():
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

                if hasattr(widget, "geometry_ctrl"):
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
            should_hide = widget.drawing and widget._cursor_settings.get("hide_on_stroke", False)
            if widget._cursor_in_viewport and not should_hide and widget.active_tool in ("brush", "eraser"):
                cur_rect = ToolCursorRenderer.get_cursor_rect(
                    widget._mouse_pos.x(), widget._mouse_pos.y(), widget.current_brush_radius, widget.zoom
                )
                if event.rect().intersects(cur_rect) or event.region().intersects(cur_rect):
                    widget.cursor_ctrl.render(painter, widget.current_brush_radius, widget.zoom, widget.drawing)
                    widget._last_rendered_cursor_rect = cur_rect
            else:
                widget.cursor_ctrl.render(painter, widget.current_brush_radius, widget.zoom, widget.drawing)
                widget._last_rendered_cursor_rect = QtCore.QRect()
            widget._last_qt_cursor_ms = (time.perf_counter() - t_cur_0) * 1000.0
        finally:
            painter.end()
            t_paint_end = time.perf_counter()
            widget._last_qt_paint_total_ms = (t_paint_end - t_paint_start) * 1000.0
            widget._last_qt_dirty_rect = event.rect()
            widget._paint_event_timestamps.append(t_paint_end)
            if len(widget._paint_event_timestamps) >= 2:
                dt = widget._paint_event_timestamps[-1] - widget._paint_event_timestamps[0]
                if dt > 0.001:
                    widget._current_viewport_fps = (len(widget._paint_event_timestamps) - 1) / dt

    @staticmethod
    def get_canvas_image(widget: RenderWidget, apply_proofing: bool = True) -> QtGui.QImage | None:
        composite = QtGui.QImage(widget.canvas_w, widget.canvas_h, QtGui.QImage.Format_RGBA8888)
        composite.fill(widget.paper_color if widget.paper_visible else QtCore.Qt.transparent)

        p = QtGui.QPainter(composite)
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "get_qimage"):
            qimg = backend.get_qimage()
            if qimg and not qimg.isNull():
                p.drawImage(0, 0, qimg)
        p.end()
        return composite
