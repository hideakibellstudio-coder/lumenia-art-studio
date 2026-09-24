"""RenderWidget — o canvas: apresenta os pixels do motor e recebe o ponteiro.

Compõe colaboradores, cada um dono do próprio estado:
  camera (CameraController) ........ zoom, pan, rotação, espelhamento
  input_router (CanvasInputRouter) . eventos de ponteiro/teclado → ações
  cursor_ctrl (CanvasCursorController) forma do cursor e anel do pincel
  stroke (CanvasStrokePipeline) .... traço interativo e regiões sujas
  viewport_renderer (ViewportRenderer) pintura e estatísticas de pintura
  tool_mgr (ToolManager) ........... controladores das ferramentas
O tamanho, a pressão manual e a cor do pincel chegam do BrushState pelo
CanvasBrushBinding; a ferramenta ativa, do ToolState pelo CanvasToolBinding.
"""

import os
import time
import math
from typing import Optional, ClassVar
from PySide6 import QtWidgets, QtCore, QtGui

try:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    _HAS_OPENGL = True
except ImportError:
    _HAS_OPENGL = False

_OPENGL_ENABLED = _HAS_OPENGL and os.environ.get("LUMENIA_DISABLE_OPENGL", "0") != "1"
_BaseCanvasWidget = QOpenGLWidget if _OPENGL_ENABLED else QtWidgets.QWidget

from ui.core.document.manager import DocumentManager
from ui.core.engine.backend import PointerEvent

from .viewport.camera_controller import CameraController
from .viewport.input_router import CanvasInputRouter
from .viewport.camera_proxies import CanvasCameraProxies
from .viewport.viewport_renderer import ViewportRenderer
from .viewport.cursor_controller import CanvasCursorController
from .viewport.canvas_stroke_pipeline import CanvasStrokePipeline
from .viewport.pointer_sample import PointerSample, event_time
from .renderers.tool_cursor_renderer import ToolCursorRenderer
from .tools.tool_manager import ToolManager
from .text_overlay_editor import TextOverlayEditor


class RenderWidget(_BaseCanvasWidget, CanvasCameraProxies):
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

        self.camera = CameraController(self)
        self.input_router = CanvasInputRouter(self)
        self.cursor_ctrl = CanvasCursorController(self)
        self.tool_mgr = ToolManager(self)

        self.stroke = CanvasStrokePipeline(self)
        self.viewport_renderer = ViewportRenderer(self)

        self.active_tool, self.drawing, self._brush_size, self.manual_pressure = "brush", False, 60.0, 0.50
        self.is_panning, self.is_zoom_dragging, self.is_space_held = False, False, False
        self.last_mouse_pos, self.zoom_drag_start_pos = QtCore.QPointF(), QtCore.QPointF()
        self.canvas_w, self.canvas_h, self.view_initialized = 1920, 1080, False
        self._last_tablet_time, self._tablet_in_use = 0.0, False
        self._active_draw_color = QtGui.QColor(0, 0, 0, 255)

        from ui.core.i18n import I18nManager
        # Método ligado (não lambda): o PySide desconecta sozinho quando o widget
        # é destruído. Um lambda num sinal de singleton ficava vivo e chamava
        # update() num RenderWidget já deletado (ex.: após fechar um documento).
        I18nManager.instance().languageChanged.connect(self._on_language_changed)

        RenderWidget._active_instance = self
        from ui.core.engine.registry import EngineRegistry
        EngineRegistry.register_viewport_telemetry_provider(RenderWidget.get_active_viewport_telemetry)

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
    def active_text_editor(self): return self.tool_mgr.active_text_editor

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
    def run_tool_command(self, command: str): self.tool_mgr.run_command(command)

    # ── Contrato com a janela principal (ui/boundary/orchestrator/workspace_port.py) ──
    def run_as_stroke(self, action):
        """Roda uma edição de pixels vinda de fora (menu) como se fosse um traço.

        Quem escuta strokeStarted/strokeFinished (documento sujo, miniaturas,
        gavetas, desfazer) reage igual a um traço. O canvas é quem emite os
        próprios sinais; antes a janela emitia os sinais do canvas por fora.
        """
        self.strokeStarted.emit()
        try:
            return action()
        finally:
            self.strokeFinished.emit()

    @property
    def is_busy(self) -> bool:
        """Traço ou transformação em andamento (não é hora de capturar recuperação)."""
        return bool(self.drawing or self.transform_ctrl.active)

    def forward_key(self, event: QtGui.QKeyEvent, pressed: bool) -> bool:
        """Tecla recebida pela janela (espaço = mão) quando o foco não está no canvas."""
        router = self.input_router
        return router.handle_key_press(event) if pressed else router.handle_key_release(event)

    def toggle_grid(self) -> bool:
        """Liga/desliga as linhas da grade de guias; devolve o novo estado."""
        guides = self.geometry_ctrl.guide_state
        visible = not guides.get("show_v", True)
        guides["show_v"] = guides["show_h"] = guides["show_d"] = visible
        self.geometry_ctrl.sync_guides_to_engine()
        self.update()
        return visible

    def toggle_rulers(self) -> bool:
        """Liga (régua reta) ou desliga as réguas; devolve o novo estado."""
        guides = self.geometry_ctrl.guide_state
        visible = guides.get("type", "none") == "none"
        guides["type"] = "straight" if visible else "none"
        self.geometry_ctrl.sync_guides_to_engine()
        self.update()
        return visible
    def clear_selection(self): self.selection_ctrl.clear_selection()
    def select_all(self): self.selection_ctrl.select_all()
    def invert_selection(self): self.selection_ctrl.invert_selection()
    def modify_selection(self, mode: str, radius_px: int) -> bool: return self.selection_ctrl.modify_selection(mode, radius_px)

    @property
    def active_color(self) -> QtGui.QColor:
        return self._active_draw_color

    @active_color.setter
    def active_color(self, color: QtGui.QColor) -> None:
        self._active_draw_color = color

    def _on_language_changed(self, *_args) -> None:
        self.update()

    # Papel: lido do documento ativo (fonte única; ver Document.set_paper).
    # Até 2026-09-24 o canvas tinha a própria cópia, escrita pelo widget de
    # papel e pela troca de documento.
    @property
    def paper_visible(self) -> bool:
        doc = DocumentManager.instance().active_document()
        return doc.paper_visible if doc is not None else True

    @property
    def paper_color(self) -> QtGui.QColor:
        doc = DocumentManager.instance().active_document()
        return doc.paper_color if doc is not None else QtGui.QColor(255, 255, 255)

    # ── Stroke & Brush Radius Delegation ──
    @property
    def backend(self):
        from ui.core.engine.registry import EngineRegistry
        return EngineRegistry.instance().get_backend()

    @property
    def current_brush_radius(self) -> float:
        # O tamanho chega do BrushState (CanvasBrushBinding). Até 2026-09-24 o
        # raio era relido do perfil inteiro do motor a cada início de traço.
        return self._brush_size / 2.0

    @property
    def brush_size(self) -> float:
        return self._brush_size

    @brush_size.setter
    def brush_size(self, val: float) -> None:
        new_val = max(0.5, float(val))
        if abs(self._brush_size - new_val) < 1e-4:
            return
        old_radius = self.current_brush_radius
        self._brush_size = new_val
        cursor = self.cursor_ctrl
        if cursor.cursor_in_viewport:
            pos = cursor.mouse_pos
            r_old = ToolCursorRenderer.get_cursor_rect(pos.x(), pos.y(), old_radius, self.zoom)
            r_new = ToolCursorRenderer.get_cursor_rect(pos.x(), pos.y(), self.current_brush_radius, self.zoom)
            self.update(r_old.united(r_new))

    def start_stroke(self, screen_x: float, screen_y: float, pressure: float, timestamp: float = 0.0, tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0):
        self.stroke.start(screen_x, screen_y, pressure, timestamp, tilt_x, tilt_y, twist)
    def paint_stroke(self, screen_x: float, screen_y: float, pressure: float, timestamp: float = 0.0, tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0):
        self.stroke.paint(screen_x, screen_y, pressure, timestamp, tilt_x, tilt_y, twist)
    def end_stroke(self, screen_x: float | None = None, screen_y: float | None = None):
        self.stroke.end(screen_x, screen_y)

    def init_engine(self, canvas_w=1920, canvas_h=1080):
        self.canvas_w, self.canvas_h = canvas_w, canvas_h
        hwnd = int(self.winId())
        backend = self.backend
        if backend is not None:  # sem motor: canvas vazio (casca pura)
            backend.init_renderer(hwnd, max(1, self.width()), max(1, self.height()), canvas_w, canvas_h)
        self.geometry_ctrl.center_on_document(canvas_w, canvas_h)
        self.center_canvas()
        self.update()

    def center_canvas(self):
        self.camera.center_canvas(self.canvas_w, self.canvas_h)
        self.publish_view(zoom_changed=True)

    def publish_view(self, zoom_changed: bool = False, notify_camera: bool = True) -> None:
        """Único caminho da câmera para fora: motor, editor de texto, repintura e sinais.

        Quem muda zoom/pan/rotação chama isto depois. `notify_camera=False`
        quando a mudança veio do próprio Navigator (evita o eco de volta).
        """
        backend = self.backend
        if backend is not None:
            backend.update_view(self.zoom, self.pan_x, self.pan_y, math.radians(self.rotation))
        if self.active_text_editor: self.active_text_editor.update_screen_position()
        self.update()
        if zoom_changed: self.zoomChanged.emit(self.zoom)
        if notify_camera:
            self.cameraChanged.emit(self.zoom, self.pan_x, self.pan_y, self.rotation, float(self.width()), float(self.height()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        top_level = self.window()
        if (top_level and top_level.isMinimized()) or self.width() <= 0 or self.height() <= 0:
            return
        if not self.view_initialized and self.width() > 100 and self.height() > 100:
            self.view_initialized = True
            self.center_canvas()
        self.update()

    def canvas_transform(self) -> QtGui.QTransform:
        return self.camera.get_canvas_transform(self.canvas_w, self.canvas_h)

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> PointerEvent:
        return self.camera.to_canvas(screen_x, screen_y, pressure, timestamp, self.canvas_w, self.canvas_h)

    def get_canvas_image(self, apply_proofing: bool = True) -> QtGui.QImage | None:
        return ViewportRenderer.get_canvas_image(self, apply_proofing)

    def paintEvent(self, event): self.viewport_renderer.render(event)

    def get_viewport_telemetry(self) -> dict:
        return self.viewport_renderer.stats.as_telemetry(_OPENGL_ENABLED)

    @classmethod
    def get_active_viewport_telemetry(cls) -> dict:
        return cls._active_instance.get_viewport_telemetry() if cls._active_instance else {}

    # ── Hardware Events ──
    def _is_synthesized_or_tablet_active(self, e: QtGui.QMouseEvent) -> bool:
        return self._tablet_in_use or (e.source() == QtCore.Qt.MouseEventSource.MouseEventSynthesizedBySystem)

    def enterEvent(self, e: QtGui.QEnterEvent):
        focused = QtWidgets.QApplication.focusWidget()
        if not isinstance(focused, (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
        self.cursor_ctrl.handle_enter(e)
        super().enterEvent(e)

    def leaveEvent(self, e: QtCore.QEvent):
        self.input_router.handle_focus_out()
        dirty = self.cursor_ctrl.handle_leave(e)
        if dirty: self.update(dirty)
        super().leaveEvent(e)

    def update_cursor_shape(self): self.cursor_ctrl.update_cursor_shape()

    def apply_cursor_settings(self, settings: dict) -> None:
        self.cursor_ctrl.apply_settings(settings)
        self.update()

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if self._is_synthesized_or_tablet_active(e): e.accept(); return
        ts = event_time(e)
        self.input_router.handle_pointer_press(e.position(), e.button(), self.manual_pressure, QtWidgets.QApplication.keyboardModifiers(), timestamp=ts)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self._is_synthesized_or_tablet_active(e): e.accept(); return
        if not self.drawing:
            dirty = self.cursor_ctrl.handle_move(e.position(), self.current_brush_radius, self.zoom, self.drawing)
            if dirty: self.update(dirty)
        ts = event_time(e)
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
        p, et = PointerSample.from_tablet(e), e.type()
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        pen = dict(timestamp=p.timestamp, tilt_x=p.tilt_x, tilt_y=p.tilt_y, twist=p.twist)
        if et == QtCore.QEvent.TabletPress:
            self._tablet_in_use = True
            self.input_router.handle_pointer_press(p.position, p.button, p.pressure, modifiers, p.is_eraser, **pen)
            e.accept()
        elif et == QtCore.QEvent.TabletMove:
            self.input_router.handle_pointer_move(p.position, p.pressure, modifiers, p.is_eraser, **pen)
            e.accept()
        elif et == QtCore.QEvent.TabletRelease:
            self._tablet_in_use = False
            self.input_router.handle_pointer_release(p.position, p.button, modifiers)
            e.accept()

    def apply_anchored_zoom(self, factor: float, cursor_pos: QtCore.QPointF):
        self.camera.zoom_at(factor, cursor_pos.x(), cursor_pos.y(), self.canvas_w, self.canvas_h)
        self.publish_view(zoom_changed=True)

    def wheelEvent(self, e: QtGui.QWheelEvent):
        angle = e.angleDelta().y() or e.angleDelta().x()
        if angle != 0:
            self.apply_anchored_zoom(1.15 ** (angle / 120.0), e.position())
            e.accept()

    def event(self, e: QtCore.QEvent) -> bool:
        if e.type() == QtCore.QEvent.NativeGesture:
            gt = getattr(e, "gestureType", lambda: None)()
            if gt == QtCore.Qt.NativeGestureType.ZoomNativeGesture:
                self.apply_anchored_zoom(1.0 + e.value(), e.position())
                return True
            elif gt == QtCore.Qt.NativeGestureType.RotateNativeGesture:
                self.rotation = (self.rotation + e.value()) % 360.0
                self.publish_view()
                return True
            elif gt == QtCore.Qt.NativeGestureType.PanNativeGesture:
                self.pan_x += e.delta().x(); self.pan_y += e.delta().y()
                self.publish_view()
                return True
        return super().event(e)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if not self.input_router.handle_key_press(e):
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e: QtGui.QKeyEvent):
        if not self.input_router.handle_key_release(e):
            super().keyReleaseEvent(e)

    def focusOutEvent(self, e: QtGui.QFocusEvent):
        self.input_router.handle_focus_out()
        super().focusOutEvent(e)


CanvasWidget = RenderWidget
__all__ = ["RenderWidget", "CanvasWidget", "TextOverlayEditor"]
