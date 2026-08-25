"""RenderWidget — High-performance interactive 2D canvas view for Lumenia."""

import time
import math
from typing import Optional
from PySide6 import QtWidgets, QtCore, QtGui

from ui.infrastructure.bridge_client import BridgeClient
from ui.infrastructure.bridge_client.dispatcher import EngineDispatcher
from ui.core.plugins.contracts import StartStrokeCommand, DrawCommand, EndStrokeCommand
from ui.core.engine.backend import PointerEvent
from ui.core.theme.manager import ThemeManager

from .text_overlay_editor import TextOverlayEditor
from .viewport.camera_controller import CameraController
from .viewport.input_router import CanvasInputRouter
from .viewport.canvas_compat import CanvasCompatMixin
from .renderers.overlay_renderer import OverlayRenderer
from .renderers.geometry_overlay_renderer import GeometryOverlayRenderer
from .tools.selection_tool_controller import SelectionToolController
from .tools.shape_tool_controller import ShapeToolController
from .tools.transform_tool_controller import TransformToolController
from .tools.eyedrop_tool_controller import EyedropToolController
from .tools.geometry_tool_controller import GeometryToolController


class RenderWidget(QtWidgets.QWidget, CanvasCompatMixin):
    """Widget de visualização e renderização do canvas com suporte nativo C++."""

    zoomChanged = QtCore.Signal(float)
    cameraChanged = QtCore.Signal(float, float, float, float, float, float)
    strokeStarted = QtCore.Signal()
    strokeFinished = QtCore.Signal()
    colorPicked = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
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

        self.active_tool = "brush"
        self.drawing = False
        self.brush_size = 60.0
        self.manual_pressure = 0.50
        self.is_panning = False
        self.is_zoom_dragging = False
        self.last_mouse_pos = QtCore.QPointF()
        self.zoom_drag_start_pos = QtCore.QPointF()

        self.canvas_w = 1920
        self.canvas_h = 1080
        self.view_initialized = False
        self._last_tablet_time: float = 0.0
        self._tablet_in_use: bool = False

        self.paper_visible: bool = True
        self.paper_color: QtGui.QColor = QtGui.QColor(255, 255, 255)
        self._checker_brush = self._create_checker_brush()

        self._active_text_editor: Optional[TextOverlayEditor] = None
        self._text_settings: dict = {
            "font_family": "Segoe UI", "font_size": 36, "bold": False,
            "italic": False, "underline": False, "align": "left",
            "color": QtGui.QColor(0, 0, 0, 255)
        }
        self._bucket_settings: dict = {
            "tolerance": 20, "expand_px": 1, "gap_closing_px": 0,
            "contiguous": True, "aa": True, "sample_all": True,
        }
        self._flood_layers: list = []
        self._flood_redo_stack: list = []

    def _create_checker_brush(self) -> QtGui.QBrush:
        pix = QtGui.QPixmap(32, 32)
        p = QtGui.QPainter(pix)
        p.fillRect(0, 0, 16, 16, QtGui.QColor("#ffffff"))
        p.fillRect(16, 0, 16, 16, QtGui.QColor("#d1d5db"))
        p.fillRect(0, 16, 16, 16, QtGui.QColor("#d1d5db"))
        p.fillRect(16, 16, 16, 16, QtGui.QColor("#ffffff"))
        p.end()
        return QtGui.QBrush(pix)

    @property
    def backend(self):
        from ui.core.engine.registry import EngineRegistry
        return EngineRegistry.instance().get_backend()

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
        from ui.core.engine.registry import EngineRegistry
        composite = QtGui.QImage(self.canvas_w, self.canvas_h, QtGui.QImage.Format_RGBA8888)
        composite.fill(self.paper_color if self.paper_visible else QtCore.Qt.transparent)

        p = QtGui.QPainter(composite)
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "get_qimage"):
            qimg = backend.get_qimage()
            if qimg and not qimg.isNull():
                p.drawImage(0, 0, qimg)
        for fl in self._flood_layers:
            if fl and not fl.isNull():
                p.drawImage(0, 0, fl)
        p.end()
        return composite

    def paintEvent(self, event):
        from ui.core.document.manager import DocumentManager
        from ui.core.engine.registry import EngineRegistry

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, self.zoom < 1.0)
        painter.fillRect(self.rect(), QtGui.QColor(128, 128, 128))

        active_doc = DocumentManager.instance().active_document()
        if active_doc is None:
            tm = ThemeManager.instance()
            painter.setPen(QtGui.QColor(tm.get_color("text_sec")))
            painter.setFont(QtGui.QFont("Segoe UI", 13, QtGui.QFont.Bold))
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, "Nenhum Documento Aberto\n\nPressione Ctrl+N para criar um novo canvas")
            painter.end()
            return

        self.canvas_w, self.canvas_h = active_doc.width, active_doc.height
        painter.save()
        painter.setTransform(self._get_canvas_transform(), combine=False)
        canvas_rect = QtCore.QRectF(0, 0, self.canvas_w, self.canvas_h)
        painter.fillRect(canvas_rect, self.paper_color if self.paper_visible else self._checker_brush)

        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "get_qimage"):
            qimg = backend.get_qimage()
            if qimg and not qimg.isNull():
                painter.drawImage(canvas_rect, qimg)

        for fl in getattr(self, "_flood_layers", []):
            if fl and not fl.isNull():
                painter.drawImage(canvas_rect, fl)

        if backend and hasattr(backend, "has_selection") and backend.has_selection():
            OverlayRenderer.render_selection_overlay(painter, backend, self.zoom, self.selection_ctrl.selection_dash_offset, self.canvas_w, self.canvas_h)

        if self.selection_ctrl.drag_active or self.selection_ctrl.lasso_is_drawing or (self.active_tool == "lasso" and len(self.selection_ctrl.lasso_points) > 0):
            OverlayRenderer.render_selection_drag_preview(painter, self, self.zoom)

        if self.transform_ctrl.active:
            OverlayRenderer.render_transform_overlay(painter, self.transform_ctrl, self.zoom)

        if self.shape_ctrl.drag_active:
            OverlayRenderer.render_shape_drag_preview(painter, self.shape_ctrl)

        # Overlays de Simetria e Guias/Réguas
        if hasattr(self, "geometry_ctrl"):
            GeometryOverlayRenderer.render_symmetry(painter, self.geometry_ctrl.sym_state, self.zoom)
            GeometryOverlayRenderer.render_guides(painter, self.geometry_ctrl, self.zoom)

        painter.restore()

        if self.eyedrop_ctrl.active and self.eyedrop_ctrl.settings.get("show_loupe", True):
            OverlayRenderer.render_color_loupe(painter, self.eyedrop_ctrl.pos, self, backend, self.eyedrop_ctrl.current_color, self.eyedrop_ctrl.old_color)
        painter.end()

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

    def set_text_settings(self, settings: dict):
        self._text_settings.update(settings)
        if self._active_text_editor: self._active_text_editor.apply_typography(settings)

    def open_text_editor(self, canvas_x: float, canvas_y: float):
        if self._active_text_editor: self.commit_text_overlay()
        self._active_text_editor = TextOverlayEditor(self, canvas_x, canvas_y, self._text_settings)
        self.update()

    def commit_text_overlay(self):
        ed = self._active_text_editor
        if not ed: return
        text = ed.get_text().strip()
        if text:
            cfg = ed.settings
            text_img = QtGui.QImage(self.canvas_w, self.canvas_h, QtGui.QImage.Format_ARGB32_Premultiplied)
            text_img.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(text_img)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
            qf = QtGui.QFont(cfg.get("font_family", "Segoe UI"), max(6, int(cfg.get("font_size", 36))))
            qf.setBold(bool(cfg.get("bold", False)))
            qf.setItalic(bool(cfg.get("italic", False)))
            qf.setUnderline(bool(cfg.get("underline", False)))
            p.setFont(qf)
            p.setPen(QtGui.QPen(QtGui.QColor(cfg.get("color", QtGui.QColor(0, 0, 0, 255)))))

            align_flags = QtCore.Qt.TextWordWrap
            al = cfg.get("align", "left")
            if al == "center": align_flags |= QtCore.Qt.AlignHCenter
            elif al == "right": align_flags |= QtCore.Qt.AlignRight
            else: align_flags |= QtCore.Qt.AlignLeft

            max_w = max(200.0, float(self.canvas_w) - ed.canvas_pos.x())
            max_h = max(200.0, float(self.canvas_h) - ed.canvas_pos.y())
            p.drawText(QtCore.QRectF(ed.canvas_pos.x(), ed.canvas_pos.y(), max_w, max_h), align_flags, text)
            p.end()

            text_rgba = text_img.convertToFormat(QtGui.QImage.Format_RGBA8888)
            px_bytes = text_rgba.constBits().tobytes()

            from ui.core.engine.registry import EngineRegistry
            b = EngineRegistry.instance().get_backend()
            if b and hasattr(b, "paste_rgba_buffer_on_active_layer") and getattr(b, "available", False):
                b.paste_rgba_buffer_on_active_layer(0, 0, self.canvas_w, self.canvas_h, px_bytes)
            else:
                self._flood_layers.append(text_img)
                self._flood_redo_stack.clear()
            self.strokeFinished.emit()

        ed.hide()
        ed.deleteLater()
        self._active_text_editor = None
        self.update()

    def cancel_text_overlay(self):
        if self._active_text_editor:
            self._active_text_editor.hide()
            self._active_text_editor.deleteLater()
            self._active_text_editor = None
            self.update()

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

    def start_stroke(self, screen_x: float, screen_y: float, pressure: float):
        self.strokeStarted.emit()
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b is not None:
            self.drawing = True
            safe_pressure = max(0.02, pressure)
            evt = self.to_canvas(screen_x, screen_y, safe_pressure, time.time())
            if hasattr(self, "geometry_ctrl"):
                self.geometry_ctrl.start_stroke_snap((evt.x, evt.y))
                cur_x, cur_y = self.geometry_ctrl.snap_point(evt.x, evt.y, self.zoom)
            else:
                cur_x, cur_y = evt.x, evt.y
            self._last_draw_pos = (cur_x, cur_y)
            b.start_stroke(cur_x, cur_y, safe_pressure)
            self.update()
            return
        if self.bridge_client.renderer is None: return
        self.drawing = True
        evt = self.to_canvas(screen_x, screen_y, max(0.02, pressure), time.time())
        self.dispatcher.dispatch(StartStrokeCommand(x=evt.x, y=evt.y, pressure=evt.pressure))
        self.update()

    def paint_stroke(self, screen_x: float, screen_y: float, pressure: float):
        if not self.drawing: return
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b is not None:
            safe_pressure = max(0.02, pressure)
            evt = self.to_canvas(screen_x, screen_y, safe_pressure, time.time())
            if hasattr(self, "geometry_ctrl"):
                cur_x, cur_y = self.geometry_ctrl.snap_point(evt.x, evt.y, self.zoom)
            else:
                cur_x, cur_y = evt.x, evt.y
            self._last_draw_pos = (cur_x, cur_y)
            b.paint_stroke(cur_x, cur_y, safe_pressure)
            self.update()
            return
        if self.bridge_client.renderer is None: return
        evt = self.to_canvas(screen_x, screen_y, pressure, time.time())
        self.dispatcher.dispatch(DrawCommand(x=evt.x, y=evt.y, pressure=evt.pressure, timestamp=time.time()))
        self.update()

    def end_stroke(self, screen_x: float | None = None, screen_y: float | None = None):
        if hasattr(self, "geometry_ctrl"):
            self.geometry_ctrl.mouse_release()
        if self.drawing:
            from ui.core.engine.registry import EngineRegistry
            b = EngineRegistry.instance().get_backend()
            if b is not None:
                if screen_x is not None and screen_y is not None:
                    evt = self.to_canvas(screen_x, screen_y, 0.0, time.time())
                    b.end_stroke(evt.x, evt.y)
                else:
                    b.end_stroke()
                self.drawing = False
                self.update()
                self.strokeFinished.emit()
                return
            if self.bridge_client.renderer is not None:
                self.dispatcher.dispatch(EndStrokeCommand())
        self.drawing = False
        self.strokeFinished.emit()

    # ── Events delegated to CanvasInputRouter ──
    def _is_synthesized_or_tablet_active(self, e: QtGui.QMouseEvent) -> bool:
        if self._tablet_in_use or (time.time() - self._last_tablet_time < 0.25):
            return True
        if e.source() == QtCore.Qt.MouseEventSource.MouseEventSynthesizedBySystem:
            return True
        return False

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if not self._is_synthesized_or_tablet_active(e):
            self.input_router.handle_pointer_press(e.position(), e.button(), self.manual_pressure, QtWidgets.QApplication.keyboardModifiers())
        else: e.ignore()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if not self._is_synthesized_or_tablet_active(e):
            self.input_router.handle_pointer_move(e.position(), self.manual_pressure, QtWidgets.QApplication.keyboardModifiers())
        else: e.ignore()

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if not self._is_synthesized_or_tablet_active(e):
            self.input_router.handle_pointer_release(e.position(), e.button(), QtWidgets.QApplication.keyboardModifiers())
        else: e.ignore()

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton and self.active_tool == "lasso" and self.selection_ctrl.lasso_points:
            self.selection_ctrl.finish_lasso_selection()
            return
        super().mouseDoubleClickEvent(e)

    def tabletEvent(self, e: QtGui.QTabletEvent):
        self._last_tablet_time = time.time()
        is_er = False
        if hasattr(e, "pointingDevice") and e.pointingDevice():
            is_er = (e.pointingDevice().pointerType() == QtGui.QPointingDevice.PointerType.Eraser)
        elif hasattr(e, "pointerType"):
            is_er = (e.pointerType() == QtGui.QPointingDevice.PointerType.Eraser)

        et = e.type()
        btn = e.button() if e.button() != QtCore.Qt.NoButton else QtCore.Qt.LeftButton
        if et == QtCore.QEvent.TabletPress:
            self._tablet_in_use = True
            self.input_router.handle_pointer_press(e.position(), btn, e.pressure(), QtWidgets.QApplication.keyboardModifiers(), is_er)
            e.accept()
        elif et == QtCore.QEvent.TabletMove:
            self.input_router.handle_pointer_move(e.position(), e.pressure(), QtWidgets.QApplication.keyboardModifiers(), is_er)
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
