import time
import math
from PySide6 import QtWidgets, QtCore, QtGui
from ui.infrastructure.bridge_client import BridgeClient
from ui.infrastructure.bridge_client.dispatcher import EngineDispatcher
from ui.core.plugins.contracts import StartStrokeCommand, DrawCommand, EndStrokeCommand
from ui.core.engine.backend import PointerEvent


class CanvasWidget(QtWidgets.QWidget):
    zoomChanged    = QtCore.Signal(float)
    cameraChanged  = QtCore.Signal(float, float, float, float, float, float)  # zoom, pan_x, pan_y, rotation, view_w, view_h
    strokeStarted  = QtCore.Signal()
    strokeFinished = QtCore.Signal()
    colorPicked    = QtCore.Signal(QtGui.QColor)  # Emitido ao capturar cor com o conta-gotas

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

        # Drawing & Tools state
        self.active_tool = "brush"
        self.drawing = False
        self.last_point = None  # (x, y, pressure) in canvas space
        self.brush_size = 60.0   # Matches the default slider size
        self.manual_pressure = 0.50

        # Conta-Gotas & Lupa Dinâmica (Color Loupe 4x HUD)
        self._eyedropper_active: bool = False
        self._eyedropper_pos: QtCore.QPointF = QtCore.QPointF()
        self._eyedrop_old_color: QtGui.QColor = QtGui.QColor(0, 0, 0)
        self._eyedrop_current_color: QtGui.QColor = QtGui.QColor(0, 0, 0)
        self._eyedrop_settings: dict = {
            "sample_size": "1x1 Ponto Único",
            "sample_radius": 0,
            "sample_all": True,
            "show_loupe": True,
        }

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

        # 7. Renderização da Lupa Dinâmica do Conta-Gotas (Color Loupe 4x HUD)
        if getattr(self, "_eyedropper_active", False) and hasattr(self, "_eyedropper_pos"):
            if self._eyedrop_settings.get("show_loupe", True):
                self._render_color_loupe(painter, self._eyedropper_pos)

        painter.end()

    def _render_color_loupe(self, painter: QtGui.QPainter, screen_pos: QtCore.QPointF):
        """Renderiza a Lupa Dinâmica (Color Loupe 4x HUD) com zoom dos pixels, mira e anel bipartido."""
        cx = screen_pos.x()
        cy = screen_pos.y() - 55.0  # Eleva a lupa acima do cursor / caneta

        r_outer = 48.0
        r_inner = 35.0

        # Mantém a lupa 100% visível na janela
        cx = max(r_outer + 8, min(float(self.width()) - r_outer - 8, cx))
        cy = max(r_outer + 8, min(float(self.height()) - r_outer - 35, cy))

        # 1. Sombra suave
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 80))
        painter.drawEllipse(QtCore.QPointF(cx, cy + 4), r_outer + 2, r_outer + 2)

        # 2. Miniatura ampliada do canvas sob a retícula (Zoom 4x)
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        qimg = backend.get_qimage() if backend and hasattr(backend, "get_qimage") else None

        painter.save()
        clip_path = QtGui.QPainterPath()
        clip_path.addEllipse(QtCore.QPointF(cx, cy), r_inner, r_inner)
        painter.setClipPath(clip_path)

        painter.fillRect(QtCore.QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2), QtGui.QColor(30, 30, 30))

        if qimg and not qimg.isNull():
            world_evt = self.to_canvas(screen_pos.x(), screen_pos.y(), 1.0, 0.0)
            wx, wy = int(world_evt.x), int(world_evt.y)

            src_size = 18
            src_x = wx - src_size // 2
            src_y = wy - src_size // 2
            src_rect = QtCore.QRect(src_x, src_y, src_size, src_size)
            target_rect = QtCore.QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2)

            cropped = qimg.copy(src_rect)
            if not cropped.isNull():
                painter.drawImage(target_rect, cropped)

        # 3. Retículo de Mira Central
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 240), 1.5))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(QtCore.QRectF(cx - 3, cy - 3, 6, 6))
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 180), 1.0))
        painter.drawRect(QtCore.QRectF(cx - 4, cy - 4, 8, 8))

        painter.restore()

        # 4. Anel Bipartido de Cores (Topo: Nova Cor | Base: Cor Anterior)
        cur_color = getattr(self, "_eyedrop_current_color", QtGui.QColor(0, 0, 0))
        old_color = getattr(self, "_eyedrop_old_color", QtGui.QColor(255, 255, 255))

        ring_thickness = r_outer - r_inner
        ring_rect = QtCore.QRectF(
            cx - r_outer + ring_thickness / 2, cy - r_outer + ring_thickness / 2,
            (r_outer - ring_thickness / 2) * 2, (r_outer - ring_thickness / 2) * 2
        )

        pen_cur = QtGui.QPen(cur_color, ring_thickness)
        pen_cur.setCapStyle(QtCore.Qt.FlatCap)
        painter.setPen(pen_cur)
        painter.drawArc(ring_rect, 0 * 16, 180 * 16)

        pen_old = QtGui.QPen(old_color, ring_thickness)
        pen_old.setCapStyle(QtCore.Qt.FlatCap)
        painter.setPen(pen_old)
        painter.drawArc(ring_rect, 180 * 16, 180 * 16)

        # Borda externa & divisores
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 140), 1.0))
        painter.drawEllipse(QtCore.QPointF(cx, cy), r_outer, r_outer)
        painter.drawEllipse(QtCore.QPointF(cx, cy), r_inner, r_inner)
        painter.drawLine(QtCore.QPointF(cx - r_outer, cy), QtCore.QPointF(cx - r_inner, cy))
        painter.drawLine(QtCore.QPointF(cx + r_inner, cy), QtCore.QPointF(cx + r_outer, cy))

        # 5. Badge com Código HEX
        badge_w, badge_h = 74.0, 18.0
        badge_rect = QtCore.QRectF(cx - badge_w / 2, cy + r_outer + 4, badge_w, badge_h)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(15, 23, 42, 220))
        painter.drawRoundedRect(badge_rect, 4, 4)

        painter.setPen(QtGui.QColor(255, 255, 255))
        fnt = QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold)
        painter.setFont(fnt)
        painter.drawText(badge_rect, QtCore.Qt.AlignCenter, cur_color.name().upper())

    def _do_eyedrop_sample(self, screen_x: float, screen_y: float) -> QtGui.QColor:
        """Executa a amostragem de cor nativa com suporte a média de área e emite o sinal."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return QtGui.QColor(0, 0, 0)

        world_evt = self.to_canvas(screen_x, screen_y, 1.0, 0.0)
        wx, wy = int(world_evt.x), int(world_evt.y)

        radius = self._eyedrop_settings.get("sample_radius", 0)
        sample_all = self._eyedrop_settings.get("sample_all", True)

        if sample_all and hasattr(backend, "pick_color_merged"):
            res = backend.pick_color_merged(wx, wy, radius)
        elif hasattr(backend, "pick_color_layer"):
            res = backend.pick_color_layer(0, wx, wy, radius)
        else:
            res = (0, 0, 0, 255)

        r, g, b, a = res[0], res[1], res[2], res[3]
        col = QtGui.QColor(r, g, b, a)
        self._eyedrop_current_color = col
        self.colorPicked.emit(col)
        return col

    def get_canvas_image(self) -> QtGui.QImage | None:
        """Retorna uma cópia do QImage do canvas renderizado pelo motor."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "get_qimage"):
            qimg = backend.get_qimage()
            if qimg and not qimg.isNull():
                return qimg.copy()
        return None

    # Stroke composition
    def start_stroke(self, screen_x: float, screen_y: float, pressure: float):
        self.strokeStarted.emit()
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
                self.strokeFinished.emit()
                return

            if self.bridge_client.renderer is not None:
                cmd = EndStrokeCommand()
                self.dispatcher.dispatch(cmd)
        self.drawing = False
        self.strokeFinished.emit()

    # Mouse handling
    def mousePressEvent(self, event):
        if event.source() != QtCore.Qt.MouseEventSource.MouseEventNotSynthesized:
            event.ignore()
            return

        modifiers = QtWidgets.QApplication.keyboardModifiers()

        # 1. Ativação do Conta-Gotas (Ferramenta eyedrop ou Atalho Alt segurado)
        if event.button() == QtCore.Qt.LeftButton and (self.active_tool == "eyedrop" or (modifiers & QtCore.Qt.AltModifier)):
            self._eyedropper_active = True
            self._eyedropper_pos = event.position()
            self._eyedrop_old_color = getattr(self, "_eyedrop_current_color", QtGui.QColor(0, 0, 0))
            self._do_eyedrop_sample(event.position().x(), event.position().y())
            self.update()
            return

        if event.button() == QtCore.Qt.LeftButton:
            if modifiers & QtCore.Qt.ShiftModifier:
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

        # Arraste com Conta-Gotas ativo
        if self._eyedropper_active:
            self._eyedropper_pos = event.position()
            self._do_eyedrop_sample(event.position().x(), event.position().y())
            self.update()
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

        if self._eyedropper_active and event.button() == QtCore.Qt.LeftButton:
            self._eyedropper_active = False
            self.update()
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
