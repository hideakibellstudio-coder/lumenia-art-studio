import time
import math
from PySide6 import QtWidgets, QtCore, QtGui
from ui.infrastructure.bridge_client import BridgeClient
from ui.infrastructure.bridge_client.dispatcher import EngineDispatcher
from ui.core.plugins.contracts import StartStrokeCommand, DrawCommand, EndStrokeCommand
from ui.core.engine.backend import PointerEvent


class CanvasWidget(QtWidgets.QWidget):
    zoomChanged = QtCore.Signal(float)
    cameraChanged = QtCore.Signal(float, float, float, float, float, float)  # zoom, pan_x, pan_y, rotation, view_w, view_h

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        # Navigation
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.rotation = 0.0  # Em graus
        self.is_panning = False
        self.last_mouse_pos = QtCore.QPointF()

        # Core structures
        self.bridge_client = BridgeClient.instance()
        self.dispatcher = EngineDispatcher.instance()

        # Drawing state
        self.drawing = False
        self.last_point = None  # (x, y, pressure) in canvas space
        self.brush_size = 60.0   # Matches the default slider size
        self.manual_pressure = 0.50

        # Canvas dimensions
        self.canvas_w = 1920
        self.canvas_h = 1080

        self.view_initialized = False

        # Papel / Fundo (Layer 0)
        self.paper_visible: bool = True
        self.paper_color: QtGui.QColor = QtGui.QColor(255, 255, 255)
        self._checker_brush = self._create_checker_brush()

    def _create_checker_brush(self) -> QtGui.QBrush:
        pix = QtGui.QPixmap(32, 32)
        p = QtGui.QPainter(pix)
        col1 = QtGui.QColor("#ffffff")
        col2 = QtGui.QColor("#d1d5db")
        p.fillRect(0, 0, 16, 16, col1)
        p.fillRect(16, 0, 16, 16, col2)
        p.fillRect(0, 16, 16, 16, col2)
        p.fillRect(16, 16, 16, 16, col1)
        p.end()
        return QtGui.QBrush(pix)

    @property
    def renderer(self):
        return self.bridge_client

    @property
    def input_adapter(self):
        return self.bridge_client.input_adapter

    def init_engine(self, canvas_w=1920, canvas_h=1080):
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h

        hwnd = int(self.winId())
        self.bridge_client.init_renderer(
            hwnd,
            max(1, self.width()),
            max(1, self.height()),
            canvas_w,
            canvas_h
        )

        self.center_canvas()
        self.update()

    def center_canvas(self):
        w = max(1, self.width())
        h = max(1, self.height())
        scale_x = w / float(self.canvas_w)
        scale_y = h / float(self.canvas_h)
        self.zoom = min(scale_x, scale_y) * 0.8
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.rotation = 0.0
        self.bridge_client.update_view(self.zoom, self.pan_x, self.pan_y, 0.0)
        self.zoomChanged.emit(self.zoom)
        self.cameraChanged.emit(self.zoom, self.pan_x, self.pan_y, self.rotation, float(w), float(h))
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        top_level = self.window()
        if top_level and top_level.isMinimized():
            return

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        if not self.view_initialized and w > 100 and h > 100:
            self.view_initialized = True
            self.center_canvas()

        self.update()

    def _get_canvas_transform(self) -> QtGui.QTransform:
        """Calcula a matriz 2D de transformação (Translate -> Rotate -> Scale -> Offset)."""
        transform = QtGui.QTransform()
        transform.translate(self.width() / 2.0 + self.pan_x, self.height() / 2.0 + self.pan_y)
        transform.rotate(self.rotation)
        transform.scale(self.zoom, self.zoom)
        transform.translate(-self.canvas_w / 2.0, -self.canvas_h / 2.0)
        return transform

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> PointerEvent:
        """Mapeia coordenadas da tela do widget para o espaço interno do canvas (0..w, 0..h)."""
        transform = self._get_canvas_transform()
        inv, ok = transform.inverted()
        if ok:
            pt = inv.map(QtCore.QPointF(screen_x, screen_y))
            return PointerEvent(x=pt.x(), y=pt.y(), pressure=pressure, timestamp=timestamp)
        return PointerEvent(x=screen_x, y=screen_y, pressure=pressure, timestamp=timestamp)

    def paintEvent(self, event):
        from ui.core.document.manager import DocumentManager
        from ui.core.engine.registry import EngineRegistry

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        # 1. Fundo do Viewport (Cinza médio neutro de estúdio estilo ALADYN ENGINE)
        painter.fillRect(self.rect(), QtGui.QColor(128, 128, 128))

        active_doc = DocumentManager.instance().active_document()
        if active_doc is None:
            painter.setPen(QtGui.QColor("#475569"))
            font_title = QtGui.QFont("Segoe UI", 13, QtGui.QFont.Bold)
            painter.setFont(font_title)
            painter.drawText(
                self.rect(),
                QtCore.Qt.AlignCenter,
                "🖼️  Nenhum Documento Aberto\n\nPressione Ctrl+N para criar um novo canvas"
            )
            painter.end()
            return

        # Sincroniza dimensões da folha
        self.canvas_w = active_doc.width
        self.canvas_h = active_doc.height

        # 2. Aplica Matriz de Transformação 2D (Translate -> Rotate -> Scale)
        painter.save()
        transform = self._get_canvas_transform()
        painter.setTransform(transform, combine=True)

        canvas_rect = QtCore.QRectF(0, 0, self.canvas_w, self.canvas_h)

        # 3. Fundo do Papel (Layer 0) ou Quadriculado de Transparência
        if not self.paper_visible:
            painter.fillRect(canvas_rect, self._checker_brush)
        else:
            painter.fillRect(canvas_rect, self.paper_color)

        # 5. Renderiza a imagem do buffer C++ do ALADYN ENGINE
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "get_qimage"):
            qimg = backend.get_qimage()
            if qimg and not qimg.isNull():
                painter.drawImage(canvas_rect, qimg)

        # 6. Moldura de borda do papel (opcional, por padrão desativada)
        if getattr(self, "show_paper_border", False):
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 100), 1.0 / max(0.01, self.zoom)))
            painter.drawRect(canvas_rect)

        painter.restore()
        painter.end()

    # Stroke composition
    def start_stroke(self, screen_x: float, screen_y: float, pressure: float):
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()

        if backend is not None:
            self.drawing = True
            evt = self.to_canvas(screen_x, screen_y, pressure, time.time())
            backend.start_stroke(evt.x, evt.y, evt.pressure)
            self.update()
            return

        if self.bridge_client.renderer is None:
            return
        self.drawing = True

        evt = self.to_canvas(screen_x, screen_y, pressure, time.time())
        cmd = StartStrokeCommand(x=evt.x, y=evt.y, pressure=evt.pressure)
        self.dispatcher.dispatch(cmd)
        self.update()

    def paint_stroke(self, screen_x: float, screen_y: float, pressure: float):
        if not self.drawing:
            return

        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()

        if backend is not None:
            evt = self.to_canvas(screen_x, screen_y, pressure, time.time())
            backend.paint_stroke(evt.x, evt.y, evt.pressure)
            self.update()
            return

        if self.bridge_client.renderer is None:
            return

        evt = self.to_canvas(screen_x, screen_y, pressure, time.time())
        cmd = DrawCommand(x=evt.x, y=evt.y, pressure=evt.pressure, timestamp=time.time())
        self.dispatcher.dispatch(cmd)
        self.update()

    def end_stroke(self, screen_x: float | None = None, screen_y: float | None = None):
        if self.drawing:
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()

            if backend is not None:
                if screen_x is not None and screen_y is not None:
                    evt = self.to_canvas(screen_x, screen_y, 0.0, time.time())
                    backend.end_stroke(evt.x, evt.y)
                else:
                    backend.end_stroke()
                self.drawing = False
                self.update()
                return

            if self.bridge_client.renderer is not None:
                cmd = EndStrokeCommand()
                self.dispatcher.dispatch(cmd)
        self.drawing = False

    # Mouse handling
    def mousePressEvent(self, event):
        if event.source() != QtCore.Qt.MouseEventSource.MouseEventNotSynthesized:
            event.ignore()
            return
        if event.button() == QtCore.Qt.LeftButton:
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers in (QtCore.Qt.ShiftModifier, QtCore.Qt.AltModifier):
                self.is_panning = True
                self.last_mouse_pos = event.position()
            else:
                self.start_stroke(event.position().x(), event.position().y(), self.manual_pressure)
        elif event.button() == QtCore.Qt.MiddleButton:
            self.is_panning = True
            self.last_mouse_pos = event.position()

    def mouseMoveEvent(self, event):
        if event.source() != QtCore.Qt.MouseEventSource.MouseEventNotSynthesized:
            event.ignore()
            return
        if self.is_panning:
            delta = event.position() - self.last_mouse_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.last_mouse_pos = event.position()
            rot_rad = math.radians(self.rotation)
            self.bridge_client.update_view(self.zoom, self.pan_x, self.pan_y, rot_rad)
            self.cameraChanged.emit(self.zoom, self.pan_x, self.pan_y, self.rotation, float(self.width()), float(self.height()))
            self.update()
        elif self.drawing:
            self.paint_stroke(event.position().x(), event.position().y(), self.manual_pressure)

    def mouseReleaseEvent(self, event):
        if event.source() != QtCore.Qt.MouseEventSource.MouseEventNotSynthesized:
            event.ignore()
            return
        if event.button() == QtCore.Qt.LeftButton and self.drawing:
            self.end_stroke(event.position().x(), event.position().y())
        elif event.button() in (QtCore.Qt.MiddleButton, QtCore.Qt.LeftButton):
            self.is_panning = False

    # Stylus and Tablet events
    def tabletEvent(self, event):
        pos = event.position()
        pressure = event.pressure()

        if event.type() == QtCore.QEvent.TabletPress:
            if event.button() == QtCore.Qt.LeftButton:
                self.start_stroke(pos.x(), pos.y(), pressure)
                event.accept()
        elif event.type() == QtCore.QEvent.TabletMove:
            if self.drawing:
                self.paint_stroke(pos.x(), pos.y(), pressure)
                event.accept()
        elif event.type() == QtCore.QEvent.TabletRelease:
            if self.drawing:
                self.end_stroke(pos.x(), pos.y())
                event.accept()

    # Zoom
    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        steps = angle / 120.0
        factor = 1.15 ** steps

        self.zoom *= factor
        self.zoom = max(0.05, min(self.zoom, 50.0))

        rot_rad = math.radians(self.rotation)
        self.bridge_client.update_view(self.zoom, self.pan_x, self.pan_y, rot_rad)
        self.update()
        self.zoomChanged.emit(self.zoom)
        self.cameraChanged.emit(self.zoom, self.pan_x, self.pan_y, self.rotation, float(self.width()), float(self.height()))
