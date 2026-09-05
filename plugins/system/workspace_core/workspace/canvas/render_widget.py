import os
import time
import math
import collections
from typing import Optional, ClassVar
from PySide6 import QtWidgets, QtCore, QtGui

try:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    _HAS_OPENGL = True
except ImportError:
    _HAS_OPENGL = False

_OPENGL_ENABLED = _HAS_OPENGL and os.environ.get("LUMENIA_DISABLE_OPENGL", "0") != "1"
_BaseCanvasWidget = QOpenGLWidget if _OPENGL_ENABLED else QtWidgets.QWidget

from ui.infrastructure.bridge_client import BridgeClient
from ui.infrastructure.bridge_client.dispatcher import EngineDispatcher
from ui.core.engine.backend import PointerEvent
from ui.core.theme.manager import ThemeManager

from .text_overlay_editor import TextOverlayEditor
from .viewport.camera_controller import CameraController
from .viewport.input_router import CanvasInputRouter
from .viewport.canvas_compat import CanvasCompatMixin
from .viewport.viewport_renderer import ViewportRenderer
from .renderers.overlay_renderer import OverlayRenderer
from .renderers.geometry_overlay_renderer import GeometryOverlayRenderer
from .renderers.tool_cursor_renderer import ToolCursorRenderer
from .tools.selection_tool_controller import SelectionToolController
from .tools.shape_tool_controller import ShapeToolController
from .tools.transform_tool_controller import TransformToolController
from .tools.eyedrop_tool_controller import EyedropToolController
from .tools.geometry_tool_controller import GeometryToolController
from .tools.text_tool_controller import TextToolController
from .viewport.cursor_controller import CanvasCursorController


class RenderWidget(_BaseCanvasWidget, CanvasCompatMixin):
    """Widget de visualização e renderização do canvas com suporte nativo C++."""

    _active_instance: ClassVar[Optional['RenderWidget']] = None

    zoomChanged = QtCore.Signal(float)
    cameraChanged = QtCore.Signal(float, float, float, float, float, float)
    strokeStarted = QtCore.Signal()
    strokeFinished = QtCore.Signal()
    colorPicked = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        if _OPENGL_ENABLED:
            fmt = QtGui.QSurfaceFormat()
            fmt.setRenderableType(QtGui.QSurfaceFormat.OpenGL)
            fmt.setVersion(3, 3)
            fmt.setProfile(QtGui.QSurfaceFormat.CoreProfile)
            fmt.setSwapInterval(0)
            self.setFormat(fmt)

        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_StaticContents)

        self.bridge_client = BridgeClient.instance()
        self.dispatcher = EngineDispatcher.instance()

        self.camera = CameraController(self)
        self.input_router = CanvasInputRouter(self)
        self.selection_ctrl = SelectionToolController(self)
        self.shape_ctrl = ShapeToolController(self)
        self.transform_ctrl = TransformToolController(self)
        self.eyedrop_ctrl = EyedropToolController(self)
        self.geometry_ctrl = GeometryToolController(self)
        self.text_ctrl = TextToolController(self)

        self.active_tool, self.drawing, self.brush_size, self.manual_pressure = "brush", False, 60.0, 0.50
        self.is_panning, self.is_zoom_dragging = False, False
        self.last_mouse_pos, self.zoom_drag_start_pos = QtCore.QPointF(), QtCore.QPointF()
        self.canvas_w, self.canvas_h, self.view_initialized = 1920, 1080, False
        self._last_tablet_time, self._tablet_in_use = 0.0, False
        self.paper_visible, self.paper_color = True, QtGui.QColor(255, 255, 255)
        self._checker_brush = self._create_checker_brush()
        self.cursor_ctrl = CanvasCursorController(self)
        self._last_rendered_cursor_rect = QtCore.QRect()
        self._bucket_settings = {"tolerance": 20, "expand_px": 1, "gap_closing_px": 0, "contiguous": True, "aa": True, "sample_all": True}
        self._flood_layers, self._flood_redo_stack = [], []
        from ui.core.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(lambda *_: self.update())

        RenderWidget._active_instance = self
        from ui.core.engine.registry import EngineRegistry
        EngineRegistry.register_viewport_telemetry_provider(RenderWidget.get_active_viewport_telemetry)
        self._last_qt_paint_total_ms = 0.0
        self._last_qt_draw_image_ms = 0.0
        self._last_qt_cursor_ms = 0.0
        self._last_qt_dirty_rect = QtCore.QRect()
        self._paint_event_timestamps = collections.deque(maxlen=60)
        self._current_viewport_fps = 0.0

    def _create_checker_brush(self) -> QtGui.QBrush:
        pix = QtGui.QPixmap(32, 32); p = QtGui.QPainter(pix)
        p.fillRect(0, 0, 16, 16, QtGui.QColor("#ffffff")); p.fillRect(16, 0, 16, 16, QtGui.QColor("#d1d5db"))
        p.fillRect(0, 16, 16, 16, QtGui.QColor("#d1d5db")); p.fillRect(16, 16, 16, 16, QtGui.QColor("#ffffff"))
        p.end()
        return QtGui.QBrush(pix)

    @property
    def backend(self):
        from ui.core.engine.registry import EngineRegistry
        return EngineRegistry.instance().get_backend()

    def sync_brush_radius(self):
        b = self.backend
        if b:
            prof_data = b.get_brush_profile_dict()
            sz = prof_data.get("brush_size", 0.0)
            if sz > 0:
                self._cached_brush_radius = float(sz) / 2.0
                return
        self._cached_brush_radius = getattr(self, "brush_size", 24.0) / 2.0

    @property
    def current_brush_radius(self) -> float:
        if not hasattr(self, "_cached_brush_radius"):
            self.sync_brush_radius()
        return self._cached_brush_radius

    @property
    def _cursor_in_viewport(self): return self.cursor_ctrl.cursor_in_viewport
    @_cursor_in_viewport.setter
    def _cursor_in_viewport(self, v): self.cursor_ctrl.cursor_in_viewport = v

    @property
    def _mouse_pos(self): return self.cursor_ctrl.mouse_pos
    @_mouse_pos.setter
    def _mouse_pos(self, v): self.cursor_ctrl.mouse_pos = v

    @property
    def _cursor_settings(self): return self.cursor_ctrl.cursor_settings
    @_cursor_settings.setter
    def _cursor_settings(self, v): self.cursor_ctrl.cursor_settings = v

    def init_engine(self, canvas_w=1920, canvas_h=1080):
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        hwnd = int(self.winId())
        self.bridge_client.init_renderer(hwnd, max(1, self.width()), max(1, self.height()), canvas_w, canvas_h)
        self.geometry_ctrl.center_on_document(canvas_w, canvas_h)
        self.center_canvas()
        self.update()

    def center_canvas(self):
        self.camera.center_canvas(self.canvas_w, self.canvas_h)
        self.bridge_client.update_view(self.zoom, self.pan_x, self.pan_y, 0.0)
        self.zoomChanged.emit(self.zoom)
        self.cameraChanged.emit(self.zoom, self.pan_x, self.pan_y, self.rotation, float(self.width()), float(self.height()))
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        top_level = self.window()
        if top_level and top_level.isMinimized():
            return
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        if not self.view_initialized and w > 100 and h > 100:
            self.view_initialized = True
            self.center_canvas()
        self.update()

    def _get_canvas_transform(self) -> QtGui.QTransform:
        return self.camera.get_canvas_transform(self.canvas_w, self.canvas_h)

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> PointerEvent:
        return self.camera.to_canvas(screen_x, screen_y, pressure, timestamp, self.canvas_w, self.canvas_h)

    def get_canvas_image(self, apply_proofing: bool = True) -> QtGui.QImage | None:
        return ViewportRenderer.get_canvas_image(self, apply_proofing)

    def paintEvent(self, event):
        ViewportRenderer.render(self, event)

    def get_viewport_telemetry(self) -> dict:
        """Retorna snapshot instantâneo do tempo de apresentação Qt na Viewport."""
        return {
            "is_gpu_accelerated": _OPENGL_ENABLED,
            "renderer_type": "OpenGL" if _OPENGL_ENABLED else "Software Raster",
            "qt_paint_total_ms": self._last_qt_paint_total_ms,
            "qt_draw_image_ms": self._last_qt_draw_image_ms,
            "qt_cursor_ms": self._last_qt_cursor_ms,
            "qt_fps": self._current_viewport_fps,
            "qt_dirty_w": self._last_qt_dirty_rect.width(),
            "qt_dirty_h": self._last_qt_dirty_rect.height(),
            "qt_dirty_area": self._last_qt_dirty_rect.width() * self._last_qt_dirty_rect.height(),
        }

    @classmethod
    def get_active_viewport_telemetry(cls) -> dict:
        """Acesso global estático à telemetria da Viewport ativa."""
        if cls._active_instance:
            return cls._active_instance.get_viewport_telemetry()
        return {}

    # ── Tool Delegation & Overlays ──
    def start_transform_mode(self) -> bool: return self.transform_ctrl.start_mode()
    def commit_transform(self): self.transform_ctrl.commit()
    def cancel_transform(self): self.transform_ctrl.cancel()
    def transform_flip_h(self): self.transform_ctrl.flip_horizontal()
    def transform_flip_v(self): self.transform_ctrl.flip_vertical()
    def transform_rotate_90(self, clockwise: bool = True): self.transform_ctrl.rotate_90(clockwise)

    def set_shape_settings(self, settings: dict):
        self.shape_ctrl.settings.update(settings)
        if self.active_tool == "shapes" or self.active_tool.startswith("shape_"): self.active_tool = "shapes"
        self.update()

    @property
    def _active_text_editor(self): return self.text_ctrl.active_editor
    @_active_text_editor.setter
    def _active_text_editor(self, val): self.text_ctrl.active_editor = val

    @property
    def _text_settings(self): return self.text_ctrl.settings
    @_text_settings.setter
    def _text_settings(self, val): self.text_ctrl.settings = val

    def set_text_settings(self, settings: dict):
        self.text_ctrl.set_settings(settings)

    def open_text_editor(self, canvas_x: float, canvas_y: float):
        self.text_ctrl.open_editor(canvas_x, canvas_y)

    def commit_text_overlay(self):
        self.text_ctrl.commit()

    def cancel_text_overlay(self):
        self.text_ctrl.cancel()

    def do_flood_fill(self, screen_x: float, screen_y: float):
        evt = self.to_canvas(screen_x, screen_y, 1.0, 0.0)
        self.strokeStarted.emit()
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "fill_area"):
            ok = b.fill_area(
                seed_x=int(evt.x), seed_y=int(evt.y),
                fill_color=getattr(self, "brush_color", QtGui.QColor(0, 0, 0, 255)),
                tolerance=self._bucket_settings.get("tolerance", 20),
                contiguous=self._bucket_settings.get("contiguous", True),
                expand_px=self._bucket_settings.get("expand_px", 1),
                gap_closing_px=self._bucket_settings.get("gap_closing_px", 0),
                aa=self._bucket_settings.get("aa", True),
                sample_all=self._bucket_settings.get("sample_all", True)
            )
            if ok:
                self.update()
                self.strokeFinished.emit()

    def clear_canvas(self):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "clear_canvas"): b.clear_canvas()
        self._flood_layers.clear()
        self._flood_redo_stack.clear()
        self.shape_ctrl.drag_active = False
        self.update()

    def start_stroke(self, screen_x: float, screen_y: float, pressure: float, timestamp: float = 0.0):
        self.sync_brush_radius()
        self.strokeStarted.emit()
        self._last_rendered_cursor_rect = QtCore.QRect()
        b = self.backend
        if b is not None:
            self.drawing = True
            safe_pressure = max(0.02, pressure)
            evt = self.to_canvas(screen_x, screen_y, safe_pressure, timestamp)
            if hasattr(self, "geometry_ctrl"):
                self.geometry_ctrl.start_stroke_snap((evt.x, evt.y))
                cur_x, cur_y = self.geometry_ctrl.snap_point(evt.x, evt.y, self.zoom)
            else:
                cur_x, cur_y = evt.x, evt.y
            self._last_draw_pos = (cur_x, cur_y)
            b.start_stroke(cur_x, cur_y, safe_pressure, timestamp)
            self.update()

    def paint_stroke(self, screen_x: float, screen_y: float, pressure: float, timestamp: float = 0.0):
        if not self.drawing: return
        b = self.backend
        if b is not None:
            self._mouse_pos = QtCore.QPointF(screen_x, screen_y)
            self.cursor_ctrl.sync_position(self._mouse_pos, self.current_brush_radius, self.zoom)
            safe_p = max(0.02, pressure)
            evt = self.to_canvas(screen_x, screen_y, safe_p, timestamp)
            cur_x, cur_y = self.geometry_ctrl.snap_point(evt.x, evt.y, self.zoom) if hasattr(self, "geometry_ctrl") else (evt.x, evt.y)
            res = b.paint_stroke(cur_x, cur_y, safe_p, timestamp)
            self._last_draw_pos = (cur_x, cur_y)
            is_sym = hasattr(self, "geometry_ctrl") and (self.geometry_ctrl.sym_state.get("mode", "none") != "none")
            has_rendered_dabs = bool(res and len(res) >= 6 and res[2] > 0 and res[3] > 0)
            if is_sym:
                self.update()
            else:
                br_rad = self.current_brush_radius
                cursor_visible = self._cursor_in_viewport and not self._cursor_settings.get("hide_on_stroke", False)
                cur_cursor_rect = ToolCursorRenderer.get_cursor_rect(screen_x, screen_y, br_rad, self.zoom) if cursor_visible else QtCore.QRect()

                if has_rendered_dabs:
                    dirty_s = self._get_canvas_transform().mapRect(QtCore.QRectF(res[0], res[1], res[2], res[3])).toAlignedRect().adjusted(-6, -6, 6, 6)
                    if cursor_visible:
                        if not self._last_rendered_cursor_rect.isEmpty():
                            dirty_s = dirty_s.united(self._last_rendered_cursor_rect)
                        dirty_s = dirty_s.united(cur_cursor_rect)
                    elif not self._last_rendered_cursor_rect.isEmpty():
                        dirty_s = dirty_s.united(self._last_rendered_cursor_rect)
                    self.update(dirty_s)
                else:
                    if cursor_visible:
                        dirty_cursor = cur_cursor_rect
                        if not self._last_rendered_cursor_rect.isEmpty():
                            dirty_cursor = dirty_cursor.united(self._last_rendered_cursor_rect)
                        self.update(dirty_cursor)
                    elif not self._last_rendered_cursor_rect.isEmpty():
                        self.update(self._last_rendered_cursor_rect)

    def end_stroke(self, screen_x: float | None = None, screen_y: float | None = None):
        if hasattr(self, "geometry_ctrl"): self.geometry_ctrl.mouse_release()
        if self.drawing:
            b = self.backend
            res = []
            if b is not None:
                if screen_x is not None and screen_y is not None:
                    evt = self.to_canvas(screen_x, screen_y, 0.0, 0.0)
                    res = b.end_stroke(evt.x, evt.y)
                    end_pos = QtCore.QPointF(screen_x, screen_y)
                else:
                    res = b.end_stroke()
                    end_pos = self._mouse_pos

                self.drawing = False
                self._mouse_pos = end_pos
                self.cursor_ctrl.sync_position(end_pos, self.current_brush_radius, self.zoom)
                self.cursor_ctrl._is_over_canvas = self.cursor_ctrl.is_over_canvas(end_pos)

                t = self._get_canvas_transform()
                dirty_to_update = QtCore.QRect()
                if res and len(res) >= 4 and res[2] > 0 and res[3] > 0:
                    dirty_c = QtCore.QRectF(res[0], res[1], res[2], res[3])
                    dirty_to_update = t.mapRect(dirty_c).toAlignedRect()

                cur_cursor_rect = ToolCursorRenderer.get_cursor_rect(
                    end_pos.x(), end_pos.y(), self.current_brush_radius, self.zoom
                )

                if not self._last_rendered_cursor_rect.isEmpty():
                    if not dirty_to_update.isEmpty():
                        dirty_to_update = dirty_to_update.united(self._last_rendered_cursor_rect)
                    else:
                        dirty_to_update = self._last_rendered_cursor_rect

                if not dirty_to_update.isEmpty():
                    dirty_to_update = dirty_to_update.united(cur_cursor_rect)
                else:
                    dirty_to_update = cur_cursor_rect

                self._last_rendered_cursor_rect = cur_cursor_rect
                self.cursor_ctrl._last_cursor_rect = cur_cursor_rect

                if not dirty_to_update.isEmpty():
                    self.update(dirty_to_update)
                self.strokeFinished.emit()
                return
        self.drawing = False
        self.strokeFinished.emit()

    # ── Events delegated to CanvasInputRouter ──
    def _is_synthesized_or_tablet_active(self, e: QtGui.QMouseEvent) -> bool:
        if self._tablet_in_use:
            return True
        if e.source() == QtCore.Qt.MouseEventSource.MouseEventSynthesizedBySystem:
            return True
        return False

    def enterEvent(self, e: QtGui.QEnterEvent):
        self.cursor_ctrl.handle_enter(e)
        super().enterEvent(e)

    def leaveEvent(self, e: QtCore.QEvent):
        dirty = self.cursor_ctrl.handle_leave(e)
        if dirty:
            self.update(dirty)
        super().leaveEvent(e)

    def _update_cursor_shape(self):
        self.cursor_ctrl.update_cursor_shape()

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if self._is_synthesized_or_tablet_active(e):
            e.accept()
            return
        ts = (e.timestamp() / 1000.0) if hasattr(e, "timestamp") and e.timestamp() > 0 else 0.0
        self.input_router.handle_pointer_press(e.position(), e.button(), self.manual_pressure, QtWidgets.QApplication.keyboardModifiers(), timestamp=ts)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self._is_synthesized_or_tablet_active(e):
            e.accept()
            return
        if not self.drawing:
            dirty = self.cursor_ctrl.handle_move(e.position(), self.current_brush_radius, self.zoom, self.drawing)
            if dirty:
                self.update(dirty)
        ts = (e.timestamp() / 1000.0) if hasattr(e, "timestamp") and e.timestamp() > 0 else 0.0
        self.input_router.handle_pointer_move(e.position(), self.manual_pressure, QtWidgets.QApplication.keyboardModifiers(), timestamp=ts)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if self._is_synthesized_or_tablet_active(e):
            e.accept()
            return
        self.input_router.handle_pointer_release(e.position(), e.button(), QtWidgets.QApplication.keyboardModifiers())

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton and self.active_tool == "lasso" and self.selection_ctrl.lasso_points:
            self.selection_ctrl.finish_lasso_selection()
            return
        super().mouseDoubleClickEvent(e)

    def tabletEvent(self, e: QtGui.QTabletEvent):
        self._last_tablet_time = time.time()
        if not self.drawing:
            dirty = self.cursor_ctrl.handle_move(e.position(), self.current_brush_radius, self.zoom, self.drawing)
            if dirty:
                self.update(dirty)
        is_er = False
        if hasattr(e, "pointingDevice") and e.pointingDevice():
            is_er = (e.pointingDevice().pointerType() == QtGui.QPointingDevice.PointerType.Eraser)
        elif hasattr(e, "pointerType"):
            is_er = (e.pointerType() == QtGui.QPointingDevice.PointerType.Eraser)

        et = e.type()
        btn = e.button() if e.button() != QtCore.Qt.NoButton else QtCore.Qt.LeftButton
        ts = (e.timestamp() / 1000.0) if hasattr(e, "timestamp") and e.timestamp() > 0 else 0.0
        if et == QtCore.QEvent.TabletPress:
            self._tablet_in_use = True
            self.input_router.handle_pointer_press(e.position(), btn, e.pressure(), QtWidgets.QApplication.keyboardModifiers(), is_er, timestamp=ts)
            e.accept()
        elif et == QtCore.QEvent.TabletMove:
            self.input_router.handle_pointer_move(e.position(), e.pressure(), QtWidgets.QApplication.keyboardModifiers(), is_er, timestamp=ts)
            e.accept()
        elif et == QtCore.QEvent.TabletRelease:
            self._tablet_in_use = False
            self.input_router.handle_pointer_release(e.position(), btn, QtWidgets.QApplication.keyboardModifiers())
            e.accept()

    def _apply_anchored_zoom(self, factor: float, cursor_pos: QtCore.QPointF):
        self.camera.zoom_at(factor, cursor_pos.x(), cursor_pos.y(), self.canvas_w, self.canvas_h)
        self.bridge_client.update_view(self.zoom, self.pan_x, self.pan_y, math.radians(self.rotation))
        if self._active_text_editor: self._active_text_editor.update_screen_position()
        self.update()
        self.zoomChanged.emit(self.zoom)
        self.cameraChanged.emit(self.zoom, self.pan_x, self.pan_y, self.rotation, float(self.width()), float(self.height()))

    def wheelEvent(self, e: QtGui.QWheelEvent):
        angle = e.angleDelta().y() or e.angleDelta().x()
        if angle != 0:
            self._apply_anchored_zoom(1.15 ** (angle / 120.0), e.position())
            e.accept()

    def event(self, e: QtCore.QEvent) -> bool:
        if e.type() == QtCore.QEvent.NativeGesture:
            gt = getattr(e, "gestureType", lambda: None)()
            if gt == QtCore.Qt.NativeGestureType.ZoomNativeGesture:
                self._apply_anchored_zoom(1.0 + e.value(), e.position())
                return True
            elif gt == QtCore.Qt.NativeGestureType.RotateNativeGesture:
                self.rotation = (self.rotation + e.value()) % 360.0
                self.bridge_client.update_view(self.zoom, self.pan_x, self.pan_y, math.radians(self.rotation))
                self.update()
                self.cameraChanged.emit(self.zoom, self.pan_x, self.pan_y, self.rotation, float(self.width()), float(self.height()))
                return True
            elif gt == QtCore.Qt.NativeGestureType.PanNativeGesture:
                self.pan_x += e.delta().x(); self.pan_y += e.delta().y()
                self.bridge_client.update_view(self.zoom, self.pan_x, self.pan_y, math.radians(self.rotation))
                self.update()
                self.cameraChanged.emit(self.zoom, self.pan_x, self.pan_y, self.rotation, float(self.width()), float(self.height()))
                return True
        return super().event(e)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if not self.input_router.handle_key_press(e):
            super().keyPressEvent(e)


CanvasWidget = RenderWidget

__all__ = ["RenderWidget", "CanvasWidget", "TextOverlayEditor"]
