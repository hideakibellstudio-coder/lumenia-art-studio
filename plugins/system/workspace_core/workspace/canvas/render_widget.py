"""RenderWidget — High-Performance Accelerated Canvas Presentation Widget.

Maintains OpenGL viewport presentation, camera transformations, and hardware event routing.
Delegates tool orchestration to ToolManager, background generation to CanvasBackgroundRenderer,
and interactive stroke processing to CanvasStrokePipeline.
Strictly decoupled in compliance with ARCcC v2 (< 270 LOC).
"""

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
from ui.core.engine.backend import PointerEvent
from ui.core.tool_settings import default_tool_settings

from .viewport.camera_controller import CameraController
from .viewport.input_router import CanvasInputRouter
from .viewport.canvas_compat import CanvasCompatMixin
from .viewport.viewport_renderer import ViewportRenderer
from .viewport.cursor_controller import CanvasCursorController
from .viewport.canvas_stroke_pipeline import CanvasStrokePipeline
from .renderers.canvas_background_renderer import CanvasBackgroundRenderer
from .tools.tool_manager import ToolManager
from .text_overlay_editor import TextOverlayEditor


class RenderWidget(_BaseCanvasWidget, CanvasCompatMixin):
    """Visualização e renderização de alta velocidade do canvas com aceleração gráfica."""

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

        self.camera = CameraController(self)
        self.input_router = CanvasInputRouter(self)
        self.cursor_ctrl = CanvasCursorController(self)
        self.tool_mgr = ToolManager(self)

        self.active_tool, self.drawing, self._brush_size, self.manual_pressure = "brush", False, 60.0, 0.50
        self._cached_brush_radius = 30.0
        self.is_panning, self.is_zoom_dragging = False, False
        self.last_mouse_pos, self.zoom_drag_start_pos = QtCore.QPointF(), QtCore.QPointF()
        self.canvas_w, self.canvas_h, self.view_initialized = 1920, 1080, False
        self._last_tablet_time, self._tablet_in_use = 0.0, False
        self.paper_visible, self.paper_color = True, QtGui.QColor(255, 255, 255)
        self._checker_brush = CanvasBackgroundRenderer.create_checker_brush()
        self._last_rendered_cursor_rect = QtCore.QRect()
        self._bucket_settings = default_tool_settings("bucket")

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

    # ── Backward Compatibility Tool Properties ──
    @property
    def selection_ctrl(self): return self.tool_mgr.selection_ctrl
    @property
    def shape_ctrl(self): return self.tool_mgr.shape_ctrl
    @property
    def transform_ctrl(self): return self.tool_mgr.transform_ctrl
    @property
    def eyedrop_ctrl(self): return self.tool_mgr.eyedrop_ctrl
    @property
    def geometry_ctrl(self): return self.tool_mgr.geometry_ctrl
    @property
    def text_ctrl(self): return self.tool_mgr.text_ctrl

    @property
    def _active_text_editor(self): return self.tool_mgr.active_text_editor
    @_active_text_editor.setter
    def _active_text_editor(self, val): self.tool_mgr.active_text_editor = val

    @property
    def _text_settings(self): return self.tool_mgr.text_settings
    @_text_settings.setter
    def _text_settings(self, val): self.tool_mgr.text_settings = val

    # ── Tool Delegation Commands ──
    def start_transform_mode(self) -> bool: return self.tool_mgr.start_transform_mode()
    def commit_transform(self): self.tool_mgr.commit_transform()
    def cancel_transform(self): self.tool_mgr.cancel_transform()
    def transform_flip_h(self): self.tool_mgr.transform_flip_h()
    def transform_flip_v(self): self.tool_mgr.transform_flip_v()
    def transform_rotate_90(self, clockwise: bool = True): self.tool_mgr.transform_rotate_90(clockwise)
    def set_shape_settings(self, settings: dict): self.tool_mgr.set_shape_settings(settings)
    def set_text_settings(self, settings: dict): self.tool_mgr.set_text_settings(settings)
    def open_text_editor(self, canvas_x: float, canvas_y: float): self.tool_mgr.open_text_editor(canvas_x, canvas_y)
    def commit_text_overlay(self): self.tool_mgr.commit_text_overlay()
    def cancel_text_overlay(self): self.tool_mgr.cancel_text_overlay()
    def do_flood_fill(self, screen_x: float, screen_y: float): self.tool_mgr.do_flood_fill(screen_x, screen_y)
    def clear_canvas(self): self.tool_mgr.clear_canvas()

    # ── Stroke & Brush Radius Delegation ──
    @property
    def backend(self):
        from ui.core.engine.registry import EngineRegistry
        return EngineRegistry.instance().get_backend()

    def sync_brush_radius(self): CanvasStrokePipeline.sync_brush_radius(self)
    @property
    def current_brush_radius(self) -> float: return CanvasStrokePipeline.get_current_brush_radius(self)
    @property
    def brush_size(self) -> float:
        return getattr(self, "_brush_size", 60.0)
    @brush_size.setter
    def brush_size(self, val: float) -> None:
        new_val = max(0.5, float(val))
        if abs(getattr(self, "_brush_size", 0.0) - new_val) < 1e-4:
            return
        old_radius = getattr(self, "_cached_brush_radius", 12.0)
        self._brush_size = new_val
        new_radius = new_val / 2.0
        self._cached_brush_radius = new_radius
        if getattr(self, "_cursor_in_viewport", False) and hasattr(self, "_mouse_pos") and hasattr(self, "zoom"):
            pos = self._mouse_pos
            from ..renderers.tool_cursor_renderer import ToolCursorRenderer
            r_old = ToolCursorRenderer.get_cursor_rect(pos.x(), pos.y(), old_radius, self.zoom)
            r_new = ToolCursorRenderer.get_cursor_rect(pos.x(), pos.y(), new_radius, self.zoom)
            self.update(r_old.united(r_new))
    def start_stroke(self, screen_x: float, screen_y: float, pressure: float, timestamp: float = 0.0, tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0):
        CanvasStrokePipeline.start_stroke(self, screen_x, screen_y, pressure, timestamp, tilt_x, tilt_y, twist)
    def paint_stroke(self, screen_x: float, screen_y: float, pressure: float, timestamp: float = 0.0, tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0):
        CanvasStrokePipeline.paint_stroke(self, screen_x, screen_y, pressure, timestamp, tilt_x, tilt_y, twist)
    def end_stroke(self, screen_x: float | None = None, screen_y: float | None = None):
        CanvasStrokePipeline.end_stroke(self, screen_x, screen_y)

    # ── Cursor Properties & Routing ──
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
        self.canvas_w, self.canvas_h = canvas_w, canvas_h
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
        if (top_level and top_level.isMinimized()) or self.width() <= 0 or self.height() <= 0:
            return
        if not self.view_initialized and self.width() > 100 and self.height() > 100:
            self.view_initialized = True
            self.center_canvas()
        self.update()

    def _get_canvas_transform(self) -> QtGui.QTransform:
        return self.camera.get_canvas_transform(self.canvas_w, self.canvas_h)

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> PointerEvent:
        return self.camera.to_canvas(screen_x, screen_y, pressure, timestamp, self.canvas_w, self.canvas_h)

    def get_canvas_image(self, apply_proofing: bool = True) -> QtGui.QImage | None:
        return ViewportRenderer.get_canvas_image(self, apply_proofing)

    def paintEvent(self, event): ViewportRenderer.render(self, event)

    def get_viewport_telemetry(self) -> dict:
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
        return cls._active_instance.get_viewport_telemetry() if cls._active_instance else {}

    # ── Hardware Events ──
    def _is_synthesized_or_tablet_active(self, e: QtGui.QMouseEvent) -> bool:
        return self._tablet_in_use or (e.source() == QtCore.Qt.MouseEventSource.MouseEventSynthesizedBySystem)

    def enterEvent(self, e: QtGui.QEnterEvent):
        self.cursor_ctrl.handle_enter(e)
        super().enterEvent(e)

    def leaveEvent(self, e: QtCore.QEvent):
        dirty = self.cursor_ctrl.handle_leave(e)
        if dirty: self.update(dirty)
        super().leaveEvent(e)

    def _update_cursor_shape(self): self.cursor_ctrl.update_cursor_shape()

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if self._is_synthesized_or_tablet_active(e): e.accept(); return
        ts = (e.timestamp() / 1000.0) if hasattr(e, "timestamp") and e.timestamp() > 0 else 0.0
        self.input_router.handle_pointer_press(e.position(), e.button(), self.manual_pressure, QtWidgets.QApplication.keyboardModifiers(), timestamp=ts)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self._is_synthesized_or_tablet_active(e): e.accept(); return
        if not self.drawing:
            dirty = self.cursor_ctrl.handle_move(e.position(), self.current_brush_radius, self.zoom, self.drawing)
            if dirty: self.update(dirty)
        ts = (e.timestamp() / 1000.0) if hasattr(e, "timestamp") and e.timestamp() > 0 else 0.0
        self.input_router.handle_pointer_move(e.position(), self.manual_pressure, QtWidgets.QApplication.keyboardModifiers(), timestamp=ts)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if self._is_synthesized_or_tablet_active(e): e.accept(); return
        self.input_router.handle_pointer_release(e.position(), e.button(), QtWidgets.QApplication.keyboardModifiers())

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton and self.active_tool == "lasso" and self.selection_ctrl.lasso_points:
            self.selection_ctrl.finish_lasso_selection(); return
        super().mouseDoubleClickEvent(e)

    def tabletEvent(self, e: QtGui.QTabletEvent):
        self._last_tablet_time = time.time()
        if not self.drawing:
            dirty = self.cursor_ctrl.handle_move(e.position(), self.current_brush_radius, self.zoom, self.drawing)
            if dirty: self.update(dirty)
        is_er = False
        if hasattr(e, "pointingDevice") and e.pointingDevice():
            is_er = (e.pointingDevice().pointerType() == QtGui.QPointingDevice.PointerType.Eraser)
        elif hasattr(e, "pointerType"):
            is_er = (e.pointerType() == QtGui.QPointingDevice.PointerType.Eraser)
        et, btn = e.type(), e.button() if e.button() != QtCore.Qt.NoButton else QtCore.Qt.LeftButton
        ts = (e.timestamp() / 1000.0) if hasattr(e, "timestamp") and e.timestamp() > 0 else 0.0
        tilt_x = float(e.xTilt()) if hasattr(e, "xTilt") else 0.0
        tilt_y = float(e.yTilt()) if hasattr(e, "yTilt") else 0.0
        twist = float(e.rotation()) if hasattr(e, "rotation") else 0.0
        if et == QtCore.QEvent.TabletPress:
            self._tablet_in_use = True
            self.input_router.handle_pointer_press(e.position(), btn, e.pressure(), QtWidgets.QApplication.keyboardModifiers(), is_er, timestamp=ts, tilt_x=tilt_x, tilt_y=tilt_y, twist=twist)
            e.accept()
        elif et == QtCore.QEvent.TabletMove:
            self.input_router.handle_pointer_move(e.position(), e.pressure(), QtWidgets.QApplication.keyboardModifiers(), is_er, timestamp=ts, tilt_x=tilt_x, tilt_y=tilt_y, twist=twist)
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
