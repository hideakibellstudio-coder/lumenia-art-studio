"""Canvas Stroke Pipeline — Execution and Dirty-Rect Tracking for Interactive Painting.

Coordinates pointer stroke dispatching to native C++ backend,
snapping through geometry controllers, cursor position synchronization,
and high-performance incremental dirty-region widget updating.
Strictly decoupled in compliance with ARCcC v2 (< 160 LOC).
"""

from typing import TYPE_CHECKING
from PySide6 import QtCore
from ..renderers.tool_cursor_renderer import ToolCursorRenderer

if TYPE_CHECKING:
    from ..render_widget import RenderWidget


class CanvasStrokePipeline:
    """Coordinates stroke lifecycles, incremental dab bounding box calculation, and updates."""

    @staticmethod
    def sync_brush_radius(widget: 'RenderWidget') -> None:
        """Synchronizes cached brush radius from the active C++ backend profile."""
        b = widget.backend
        if b:
            prof_data = b.get_brush_profile_dict()
            sz = prof_data.get("brush_size", 0.0)
            if sz > 0:
                widget._cached_brush_radius = float(sz) / 2.0
                return
        widget._cached_brush_radius = getattr(widget, "brush_size", 24.0) / 2.0

    @staticmethod
    def get_current_brush_radius(widget: 'RenderWidget') -> float:
        """Returns the current brush radius, updating the cache if needed."""
        if not hasattr(widget, "_cached_brush_radius"):
            CanvasStrokePipeline.sync_brush_radius(widget)
        return widget._cached_brush_radius

    @staticmethod
    def start_stroke(
        widget: 'RenderWidget',
        screen_x: float,
        screen_y: float,
        pressure: float,
        timestamp: float = 0.0
    ) -> None:
        """Initializes a new brush stroke, snaps origin point, and dispatches to backend."""
        CanvasStrokePipeline.sync_brush_radius(widget)
        widget.strokeStarted.emit()
        widget._last_rendered_cursor_rect = QtCore.QRect()
        b = widget.backend
        if b is not None:
            widget.drawing = True
            safe_pressure = max(0.02, pressure)
            evt = widget.to_canvas(screen_x, screen_y, safe_pressure, timestamp)
            if hasattr(widget, "geometry_ctrl"):
                widget.geometry_ctrl.start_stroke_snap((evt.x, evt.y))
                cur_x, cur_y = widget.geometry_ctrl.snap_point(evt.x, evt.y, widget.zoom)
            else:
                cur_x, cur_y = evt.x, evt.y
            widget._last_draw_pos = (cur_x, cur_y)
            b.start_stroke(cur_x, cur_y, safe_pressure, timestamp)
            widget.update()

    @staticmethod
    def paint_stroke(
        widget: 'RenderWidget',
        screen_x: float,
        screen_y: float,
        pressure: float,
        timestamp: float = 0.0
    ) -> None:
        """Feeds motion events to backend, calculating dirty rect union between dabs and cursor."""
        if not widget.drawing:
            return
        b = widget.backend
        if b is not None:
            widget._mouse_pos = QtCore.QPointF(screen_x, screen_y)
            widget.cursor_ctrl.sync_position(widget._mouse_pos, widget.current_brush_radius, widget.zoom)
            safe_p = max(0.02, pressure)
            evt = widget.to_canvas(screen_x, screen_y, safe_p, timestamp)
            cur_x, cur_y = widget.geometry_ctrl.snap_point(evt.x, evt.y, widget.zoom) if hasattr(widget, "geometry_ctrl") else (evt.x, evt.y)
            res = b.paint_stroke(cur_x, cur_y, safe_p, timestamp)
            widget._last_draw_pos = (cur_x, cur_y)
            is_sym = hasattr(widget, "geometry_ctrl") and (widget.geometry_ctrl.sym_state.get("mode", "none") != "none")
            has_rendered_dabs = bool(res and len(res) >= 6 and res[2] > 0 and res[3] > 0)

            if is_sym:
                widget.update()
            else:
                br_rad = widget.current_brush_radius
                cursor_visible = widget._cursor_in_viewport and not widget._cursor_settings.get("hide_on_stroke", False)
                cur_cursor_rect = ToolCursorRenderer.get_cursor_rect(screen_x, screen_y, br_rad, widget.zoom) if cursor_visible else QtCore.QRect()

                if has_rendered_dabs:
                    dirty_s = widget._get_canvas_transform().mapRect(QtCore.QRectF(res[0], res[1], res[2], res[3])).toAlignedRect().adjusted(-6, -6, 6, 6)
                    if cursor_visible:
                        if not widget._last_rendered_cursor_rect.isEmpty():
                            dirty_s = dirty_s.united(widget._last_rendered_cursor_rect)
                        dirty_s = dirty_s.united(cur_cursor_rect)
                    elif not widget._last_rendered_cursor_rect.isEmpty():
                        dirty_s = dirty_s.united(widget._last_rendered_cursor_rect)
                    widget.update(dirty_s)
                else:
                    if cursor_visible:
                        dirty_cursor = cur_cursor_rect
                        if not widget._last_rendered_cursor_rect.isEmpty():
                            dirty_cursor = dirty_cursor.united(widget._last_rendered_cursor_rect)
                        widget.update(dirty_cursor)
                    elif not widget._last_rendered_cursor_rect.isEmpty():
                        widget.update(widget._last_rendered_cursor_rect)

    @staticmethod
    def end_stroke(
        widget: 'RenderWidget',
        screen_x: float | None = None,
        screen_y: float | None = None
    ) -> None:
        """Finalizes an active brush stroke and updates dirty canvas region."""
        if hasattr(widget, "geometry_ctrl"):
            widget.geometry_ctrl.mouse_release()
        if widget.drawing:
            b = widget.backend
            res = []
            if b is not None:
                if screen_x is not None and screen_y is not None:
                    evt = widget.to_canvas(screen_x, screen_y, 0.0, 0.0)
                    res = b.end_stroke(evt.x, evt.y)
                    end_pos = QtCore.QPointF(screen_x, screen_y)
                else:
                    res = b.end_stroke()
                    end_pos = widget._mouse_pos

                widget.drawing = False
                widget._mouse_pos = end_pos
                widget.cursor_ctrl.sync_position(end_pos, widget.current_brush_radius, widget.zoom)
                widget.cursor_ctrl._is_over_canvas = widget.cursor_ctrl.is_over_canvas(end_pos)

                t = widget._get_canvas_transform()
                dirty_to_update = QtCore.QRect()
                if res and len(res) >= 4 and res[2] > 0 and res[3] > 0:
                    dirty_c = QtCore.QRectF(res[0], res[1], res[2], res[3])
                    dirty_to_update = t.mapRect(dirty_c).toAlignedRect()

                cur_cursor_rect = ToolCursorRenderer.get_cursor_rect(
                    end_pos.x(), end_pos.y(), widget.current_brush_radius, widget.zoom
                )

                if not widget._last_rendered_cursor_rect.isEmpty():
                    if not dirty_to_update.isEmpty():
                        dirty_to_update = dirty_to_update.united(widget._last_rendered_cursor_rect)
                    else:
                        dirty_to_update = widget._last_rendered_cursor_rect

                if not dirty_to_update.isEmpty():
                    dirty_to_update = dirty_to_update.united(cur_cursor_rect)
                else:
                    dirty_to_update = cur_cursor_rect

                widget._last_rendered_cursor_rect = cur_cursor_rect
                widget.cursor_ctrl._last_cursor_rect = cur_cursor_rect

                if not dirty_to_update.isEmpty():
                    widget.update(dirty_to_update)
                widget.strokeFinished.emit()
                return

        widget.drawing = False
        widget.strokeFinished.emit()
