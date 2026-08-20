import time
import math
from PySide6 import QtWidgets, QtCore, QtGui
from ui.infrastructure.bridge_client import BridgeClient
from ui.infrastructure.bridge_client.dispatcher import EngineDispatcher
from ui.core.plugins.contracts import StartStrokeCommand, DrawCommand, EndStrokeCommand
from ui.core.engine.backend import PointerEvent
from ui.core.theme.manager import ThemeManager


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

        # Balde de Tinta (Flood Fill Settings)
        self._bucket_settings: dict = {
            "tolerance": 20,
            "expand_px": 1,
            "gap_closing_px": 0,
            "contiguous": True,
            "aa": True,
            "sample_all": True,
        }
        self._active_draw_color: QtGui.QColor = QtGui.QColor(0, 0, 0, 255)
        self._flood_layers: list[QtGui.QImage] = []
        self._flood_redo_stack: list[QtGui.QImage] = []

        # Seleções (Magic Wand, Rect, Ellipse, Lasso)
        self._wand_settings: dict = {
            "tolerance": 20,
            "expand_px": 0,
            "contiguous": True,
            "aa": True,
            "sample_all": True,
            "mode": 0,
        }
        self._geom_select_settings: dict = {
            "feather_px": 0,
            "aa": True,
            "mode": 0,
        }
        self._lasso_settings: dict = {
            "lasso_type": "freehand",
            "feather_px": 0,
            "aa": True,
            "mode": 0,
        }
        self._sel_drag_active: bool = False
        self._sel_drag_start: QtCore.QPointF = QtCore.QPointF(0, 0)
        self._sel_drag_current: QtCore.QPointF = QtCore.QPointF(0, 0)
        self._lasso_points: list[QtCore.QPointF] = []
        self._lasso_is_drawing: bool = False
        self._lasso_hover_pt: Optional[QtCore.QPointF] = None

        self._selection_dash_offset: float = 0.0
        self._selection_timer = QtCore.QTimer(self)
        self._selection_timer.setInterval(60)
        self._selection_timer.timeout.connect(self._on_selection_timer_tick)

        # Transform Tool State
        self._transform_active: bool = False
        self._transform_source_qimage: Optional[QtGui.QImage] = None
        self._transform_source_rect: QtCore.QRectF = QtCore.QRectF()
        self._transform_pivot: QtCore.QPointF = QtCore.QPointF()
        self._transform_dx: float = 0.0
        self._transform_dy: float = 0.0
        self._transform_scale_x: float = 1.0
        self._transform_scale_y: float = 1.0
        self._transform_rotation: float = 0.0
        self._transform_flip_h: bool = False
        self._transform_flip_v: bool = False
        self._transform_interp_mode: int = 2
        self._transform_lock_aspect: bool = False
        self._transform_handle_dragged: Optional[str] = None
        self._transform_mouse_press_pos: Optional[QtCore.QPointF] = None
        self._transform_press_params: dict = {}

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
            tm = ThemeManager.instance()
            painter.setPen(QtGui.QColor(tm.get_color("text_sec")))
            font_title = QtGui.QFont("Segoe UI", 13, QtGui.QFont.Bold)
            painter.setFont(font_title)
            painter.drawText(
                self.rect(),
                QtCore.Qt.AlignCenter,
                "Nenhum Documento Aberto\n\nPressione Ctrl+N para criar um novo canvas"
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

        # 4. Renderiza a imagem do buffer C++ do ALADYN ENGINE (com aceleração de perfil de cor nativa)
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "get_qimage"):
            qimg = backend.get_qimage()
            if qimg and not qimg.isNull():
                painter.drawImage(canvas_rect, qimg)

        # 5. Renderiza camadas de preenchimento do Balde de Tinta
        for fl in getattr(self, "_flood_layers", []):
            if fl and not fl.isNull():
                painter.drawImage(canvas_rect, fl)

        # 6. Renderização da Seleção Ativa (Marching Ants / Contorno Animado)
        if backend and hasattr(backend, "has_selection") and backend.has_selection():
            self._render_selection_overlay(painter, backend)

        # 6.5. Renderização do Preview de Arrasto/Criação de Seleção (Retângulo / Elipse / Laço)
        if getattr(self, "_sel_drag_active", False) or getattr(self, "_lasso_is_drawing", False) or (self.active_tool == "lasso" and len(getattr(self, "_lasso_points", [])) > 0):
            self._render_selection_drag_preview(painter)

        # 6.7. Renderização da Transformação Livre (Bounding Box com 8 alças e pivô)
        if getattr(self, "_transform_active", False):
            self._render_transform_overlay(painter)

        # 7. Moldura de borda do papel (opcional, por padrão desativada)
        if getattr(self, "show_paper_border", False):
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 100), 1.0 / max(0.01, self.zoom)))
            painter.drawRect(canvas_rect)

        painter.restore()

        # 8. Renderização da Lupa Dinâmica do Conta-Gotas (Color Loupe 4x HUD)
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
        """Executa a amostragem de cor WYSIWYG no canvas visível com suporte a raio de média."""
        world_evt = self.to_canvas(screen_x, screen_y, 1.0, 0.0)
        wx = int(max(0, min(self.canvas_w - 1, world_evt.x)))
        wy = int(max(0, min(self.canvas_h - 1, world_evt.y)))

        composite = self.get_canvas_image()
        if not composite or composite.isNull():
            return QtGui.QColor(0, 0, 0)

        radius = int(self._eyedrop_settings.get("sample_radius", 0))

        if radius <= 0:
            col = composite.pixelColor(wx, wy)
        else:
            # Média dos canais RGBA na vizinhança de raio configurado
            r_acc, g_acc, b_acc, a_acc, count = 0, 0, 0, 0, 0
            x_min = max(0, wx - radius)
            x_max = min(self.canvas_w - 1, wx + radius)
            y_min = max(0, wy - radius)
            y_max = min(self.canvas_h - 1, wy + radius)

            for py in range(y_min, y_max + 1):
                for px in range(x_min, x_max + 1):
                    p_col = composite.pixelColor(px, py)
                    r_acc += p_col.red()
                    g_acc += p_col.green()
                    b_acc += p_col.blue()
                    a_acc += p_col.alpha()
                    count += 1

            if count > 0:
                col = QtGui.QColor(
                    int(r_acc / count),
                    int(g_acc / count),
                    int(b_acc / count),
                    int(a_acc / count),
                )
            else:
                col = composite.pixelColor(wx, wy)

        self._eyedrop_current_color = col
        self.colorPicked.emit(col)
        return col

    def get_canvas_image(self, apply_proofing: bool = True) -> QtGui.QImage | None:
        """Retorna uma cópia do QImage composto do canvas (Papel + Buffer C++ + Preenchimentos + Prova de Cores)."""
        from ui.core.engine.registry import EngineRegistry
        from ui.core.engine.color_profile import ColorProfileEngine

        composite = QtGui.QImage(self.canvas_w, self.canvas_h, QtGui.QImage.Format_RGBA8888)
        if self.paper_visible:
            composite.fill(self.paper_color)
        else:
            composite.fill(QtCore.Qt.transparent)

        p = QtGui.QPainter(composite)
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "get_qimage"):
            qimg = backend.get_qimage()
            if qimg and not qimg.isNull():
                p.drawImage(0, 0, qimg)

        if getattr(self, "_flood_layers", None):
            for fl in self._flood_layers:
                if fl and not fl.isNull():
                    p.drawImage(0, 0, fl)
        p.end()

        # O qimg do backend nativo C++ já entrega o buffer com o perfil de cor acelerado em C++ (< 0.1ms)
        return composite

    def update_bucket_settings(self, settings: dict):
        self._bucket_settings.update(settings)

    def do_flood_fill(self, screen_x: float, screen_y: float):
        """Executa preenchimento inteligente instantâneo da região clicada no canvas."""
        world_evt = self.to_canvas(screen_x, screen_y, 1.0, 0.0)
        wx, wy = int(world_evt.x), int(world_evt.y)

        # Cor de preenchimento atual
        fill_color = getattr(self, "brush_color", QtGui.QColor(0, 0, 0, 255))
        if hasattr(self, "_active_draw_color") and self._active_draw_color:
            fill_color = self._active_draw_color

        tol = self._bucket_settings.get("tolerance", 20)
        contig = self._bucket_settings.get("contiguous", True)
        expand = self._bucket_settings.get("expand_px", 1)
        gap = self._bucket_settings.get("gap_closing_px", 0)
        aa = self._bucket_settings.get("aa", True)
        sample_all = self._bucket_settings.get("sample_all", True)

        self.strokeStarted.emit()

        # 1. Executa no motor nativo C++ (ultra-rápido, direto nos tiles de memória)
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "fill_area"):
            ok = backend.fill_area(
                seed_x=wx,
                seed_y=wy,
                fill_color=fill_color,
                tolerance=tol,
                contiguous=contig,
                expand_px=expand,
                gap_closing_px=gap,
                aa=aa,
                sample_all=sample_all,
            )
            if ok:
                self.update()
                self.strokeFinished.emit()
                return

        # 2. Fallback para FloodFillEngine em modo casca pura
        from ui.core.engine.flood_fill import FloodFillEngine
        base_img = self.get_canvas_image()
        if base_img and not base_img.isNull():
            fill_layer = FloodFillEngine.flood_fill(
                base_img,
                seed_x=wx,
                seed_y=wy,
                fill_color=fill_color,
                tolerance=tol,
                contiguous=contig,
                expand_px=expand,
                gap_closing_px=gap,
                anti_aliasing=aa,
            )

            if fill_layer and not fill_layer.isNull():
                self._flood_layers.append(fill_layer)
                self._flood_redo_stack.clear()
                self.update()
                self.strokeFinished.emit()

    # ── Varinha Mágica (Magic Wand & Marching Ants) ──────────────────────────

    def update_wand_settings(self, settings: dict):
        self._wand_settings.update(settings)

    def _on_selection_timer_tick(self):
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "has_selection") and backend.has_selection():
            self._selection_dash_offset = (self._selection_dash_offset + 1.0) % 16.0
            self.update()
        else:
            self._selection_timer.stop()

    def do_magic_wand_select(self, screen_x: float, screen_y: float):
        """Executa a seleção inteligente da Varinha Mágica a partir do ponto clicado."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return

        world_evt = self.to_canvas(screen_x, screen_y, 1.0, 0.0)
        wx, wy = int(world_evt.x), int(world_evt.y)

        if wx < 0 or wx >= self.canvas_w or wy < 0 or wy >= self.canvas_h:
            return

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if (modifiers & QtCore.Qt.ShiftModifier) and (modifiers & QtCore.Qt.AltModifier):
            mode = 3  # Intersect
        elif modifiers & QtCore.Qt.ShiftModifier:
            mode = 1  # Add (+)
        elif modifiers & QtCore.Qt.AltModifier:
            mode = 2  # Subtract (-)
        else:
            mode = self._wand_settings.get("mode", 0)

        tol = int(self._wand_settings.get("tolerance", 20))
        contig = bool(self._wand_settings.get("contiguous", True))
        exp = int(self._wand_settings.get("expand_px", 0))
        aa = bool(self._wand_settings.get("aa", True))
        sample_all = bool(self._wand_settings.get("sample_all", True))

        ok = False
        if hasattr(backend, "magic_wand_select"):
            ok = backend.magic_wand_select(
                seed_x=wx,
                seed_y=wy,
                tolerance=tol,
                contiguous=contig,
                expand_px=exp,
                anti_aliasing=aa,
                mode=mode,
                sample_all_layers=sample_all
            )

        if ok and backend.has_selection():
            if not self._selection_timer.isActive():
                self._selection_timer.start()
        else:
            self._selection_timer.stop()

        self.update()

    def _render_selection_overlay(self, painter: QtGui.QPainter, backend):
        """Renderiza o contorno animado de formigas marchantes (Marching Ants) clássico sem obstruir a arte."""
        bounds = backend.get_selection_bounds() if hasattr(backend, "get_selection_bounds") else (0, 0, self.canvas_w, self.canvas_h)
        bx, by, bw, bh = bounds
        if bw <= 0 or bh <= 0:
            return

        loops = backend.get_selection_contour_loops() if hasattr(backend, "get_selection_contour_loops") else []

        path = QtGui.QPainterPath()
        if loops:
            for loop in loops:
                if len(loop) >= 4:
                    poly = QtGui.QPolygonF([
                        QtCore.QPointF(loop[i], loop[i+1])
                        for i in range(0, len(loop), 2)
                    ])
                    path.addPolygon(poly)
        else:
            path.addRect(QtCore.QRectF(bx, by, bw, bh))

        painter.save()
        zoom_factor = max(0.01, self.zoom)
        line_w = 1.0 / zoom_factor

        pen_black = QtGui.QPen(QtGui.QColor(0, 0, 0, 255), line_w)
        pen_black.setStyle(QtCore.Qt.CustomDashLine)
        pen_black.setDashPattern([4, 4])
        pen_black.setDashOffset(self._selection_dash_offset)

        pen_white = QtGui.QPen(QtGui.QColor(255, 255, 255, 255), line_w)
        pen_white.setStyle(QtCore.Qt.CustomDashLine)
        pen_white.setDashPattern([4, 4])
        pen_white.setDashOffset(self._selection_dash_offset + 4.0)

        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(pen_black)
        painter.drawPath(path)
        painter.setPen(pen_white)
        painter.drawPath(path)
        painter.restore()

    def _render_selection_drag_preview(self, painter: QtGui.QPainter):
        """Renderiza a linha pontilhada de preview em tempo real durante a criação de seleção."""
        painter.save()
        zoom_factor = max(0.01, self.zoom)
        line_w = 1.0 / zoom_factor

        pen_black = QtGui.QPen(QtGui.QColor(0, 0, 0, 255), line_w)
        pen_black.setStyle(QtCore.Qt.CustomDashLine)
        pen_black.setDashPattern([4, 4])

        pen_white = QtGui.QPen(QtGui.QColor(255, 255, 255, 255), line_w)
        pen_white.setStyle(QtCore.Qt.CustomDashLine)
        pen_white.setDashPattern([4, 4])
        pen_white.setDashOffset(4.0)

        painter.setBrush(QtCore.Qt.NoBrush)

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        is_shift = bool(modifiers & QtCore.Qt.ShiftModifier)
        is_alt = bool(modifiers & QtCore.Qt.AltModifier)

        if self.active_tool in ("rect_select", "ellipse_select") and getattr(self, "_sel_drag_active", False):
            p1 = self._sel_drag_start
            p2 = self._sel_drag_current
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()

            if is_shift:
                side = max(abs(dx), abs(dy))
                dx = side if dx >= 0 else -side
                dy = side if dy >= 0 else -side

            if is_alt:
                rx = abs(dx)
                ry = abs(dy)
                rect = QtCore.QRectF(p1.x() - rx, p1.y() - ry, rx * 2.0, ry * 2.0)
            else:
                rect = QtCore.QRectF(min(p1.x(), p1.x() + dx), min(p1.y(), p1.y() + dy), abs(dx), abs(dy))

            if self.active_tool == "rect_select":
                painter.setPen(pen_black)
                painter.drawRect(rect)
                painter.setPen(pen_white)
                painter.drawRect(rect)
            elif self.active_tool == "ellipse_select":
                painter.setPen(pen_black)
                painter.drawEllipse(rect)
                painter.setPen(pen_white)
                painter.drawEllipse(rect)

        elif self.active_tool == "lasso":
            pts = getattr(self, "_lasso_points", [])
            if len(pts) >= 1:
                path = QtGui.QPainterPath()
                path.moveTo(pts[0])
                for p in pts[1:]:
                    path.lineTo(p)

                if self._lasso_settings.get("lasso_type") == "polygonal" and getattr(self, "_lasso_hover_pt", None):
                    path.lineTo(self._lasso_hover_pt)

                painter.setPen(pen_black)
                painter.drawPath(path)
                painter.setPen(pen_white)
                painter.drawPath(path)

        painter.restore()

    def _finish_geom_selection(self):
        """Finaliza a criação de seleção retangular ou elíptica e despacha para o motor nativo."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        is_shift = bool(modifiers & QtCore.Qt.ShiftModifier)
        is_alt = bool(modifiers & QtCore.Qt.AltModifier)

        p1 = self._sel_drag_start
        p2 = self._sel_drag_current

        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()

        if is_shift:
            side = max(abs(dx), abs(dy))
            dx = side if dx >= 0 else -side
            dy = side if dy >= 0 else -side

        if is_alt:
            rx = abs(dx)
            ry = abs(dy)
            cx = p1.x()
            cy = p1.y()
            x = cx - rx
            y = cy - ry
            w = rx * 2.0
            h = ry * 2.0
        else:
            x = min(p1.x(), p1.x() + dx)
            y = min(p1.y(), p1.y() + dy)
            w = abs(dx)
            h = abs(dy)
            cx = x + w / 2.0
            cy = y + h / 2.0
            rx = w / 2.0
            ry = h / 2.0

        if w < 2 or h < 2:
            return

        cfg = getattr(self, "_geom_select_settings", {})
        if (modifiers & QtCore.Qt.ShiftModifier) and (modifiers & QtCore.Qt.AltModifier):
            mode = 3
        elif modifiers & QtCore.Qt.ShiftModifier and not is_alt:
            mode = 1
        elif modifiers & QtCore.Qt.AltModifier and not is_shift:
            mode = 2
        else:
            mode = cfg.get("mode", 0)

        feather_px = int(cfg.get("feather_px", 0))
        aa = bool(cfg.get("aa", True))

        if self.active_tool == "rect_select":
            if hasattr(backend, "select_rect"):
                backend.select_rect(int(x), int(y), int(w), int(h), mode=mode, feather_px=feather_px)
        elif self.active_tool == "ellipse_select":
            if hasattr(backend, "select_ellipse"):
                backend.select_ellipse(int(cx), int(cy), int(rx), int(ry), mode=mode, anti_aliasing=aa, feather_px=feather_px)

        if hasattr(backend, "has_selection") and backend.has_selection():
            if not self._selection_timer.isActive():
                self._selection_timer.start()
        else:
            self._selection_timer.stop()

        self.update()

    def _finish_lasso_selection(self):
        """Finaliza a seleção por laço e despacha para o motor nativo."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if not backend or len(getattr(self, "_lasso_points", [])) < 3:
            self._lasso_points = []
            self.update()
            return

        flat_pts = []
        for pt in self._lasso_points:
            flat_pts.append(int(pt.x()))
            flat_pts.append(int(pt.y()))

        self._lasso_points = []

        cfg = getattr(self, "_lasso_settings", {})
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if (modifiers & QtCore.Qt.ShiftModifier) and (modifiers & QtCore.Qt.AltModifier):
            mode = 3
        elif modifiers & QtCore.Qt.ShiftModifier:
            mode = 1
        elif modifiers & QtCore.Qt.AltModifier:
            mode = 2
        else:
            mode = cfg.get("mode", 0)

        feather_px = int(cfg.get("feather_px", 0))
        aa = bool(cfg.get("aa", True))

        if hasattr(backend, "select_polygon"):
            backend.select_polygon(flat_pts, mode=mode, anti_aliasing=aa, feather_px=feather_px)

        if hasattr(backend, "has_selection") and backend.has_selection():
            if not self._selection_timer.isActive():
                self._selection_timer.start()
        else:
            self._selection_timer.stop()

        self.update()

    # ── Ferramenta de Transformação Livre (Transform Tool) ──────────────────

    def start_transform_mode(self) -> bool:
        """Inicia a transformação interativa da camada ou seleção ativa."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if not backend or not hasattr(backend, "begin_transform"):
            return False

        if not backend.begin_transform():
            return False

        bx, by, bw, bh = backend.get_transform_source_bounds()
        px, py = backend.get_transform_pivot()
        qimg = backend.get_transform_source_qimage()

        self._transform_source_rect = QtCore.QRectF(bx, by, bw, bh)
        self._transform_pivot = QtCore.QPointF(px, py)
        self._transform_source_qimage = qimg
        self._transform_dx = 0.0
        self._transform_dy = 0.0
        self._transform_scale_x = 1.0
        self._transform_scale_y = 1.0
        self._transform_rotation = 0.0
        self._transform_flip_h = False
        self._transform_flip_v = False
        self._transform_active = True
        self.update()
        return True

    def commit_transform(self):
        """Aplica definitivamente a transformação nos tiles em C++ e recompõe."""
        if not self._transform_active:
            return
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "commit_transform"):
            backend.commit_transform(
                dx=self._transform_dx,
                dy=self._transform_dy,
                scale_x=self._transform_scale_x,
                scale_y=self._transform_scale_y,
                rotation_deg=self._transform_rotation,
                pivot_x=self._transform_pivot.x(),
                pivot_y=self._transform_pivot.y(),
                flip_h=self._transform_flip_h,
                flip_v=self._transform_flip_v,
                interp_mode=getattr(self, "_transform_interp_mode", 2)
            )
        self._transform_active = False
        self._transform_source_qimage = None
        self.update()
        self.strokeFinished.emit()

    def cancel_transform(self):
        """Cancela a transformação e restaura a camada ativa."""
        if not self._transform_active:
            return
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "cancel_transform"):
            backend.cancel_transform()
        self._transform_active = False
        self._transform_source_qimage = None
        self.update()

    def transform_flip_h(self):
        if self._transform_active:
            self._transform_flip_h = not self._transform_flip_h
            self.update()

    def transform_flip_v(self):
        if self._transform_active:
            self._transform_flip_v = not self._transform_flip_v
            self.update()

    def transform_rotate_90(self, clockwise: bool = True):
        if self._transform_active:
            delta = 90.0 if clockwise else -90.0
            self._transform_rotation = (self._transform_rotation + delta) % 360.0
            self.update()

    def _get_transform_matrix(self) -> QtGui.QTransform:
        """Calcula a matriz afim 2D acumulada da transformação."""
        t = QtGui.QTransform()
        pv = self._transform_pivot
        t.translate(pv.x() + self._transform_dx, pv.y() + self._transform_dy)
        t.rotate(self._transform_rotation)
        sx = -self._transform_scale_x if self._transform_flip_h else self._transform_scale_x
        sy = -self._transform_scale_y if self._transform_flip_v else self._transform_scale_y
        t.scale(sx, sy)
        t.translate(-pv.x(), -pv.y())
        return t

    def _render_transform_overlay(self, painter: QtGui.QPainter):
        """Renderiza a imagem transformada em tempo real, bounding box com 8 alças e pivô."""
        if not self._transform_active or not self._transform_source_qimage:
            return

        t_mat = self._get_transform_matrix()
        src_rect = self._transform_source_rect
        pv = self._transform_pivot

        # 1. Renderiza o conteúdo da imagem transformado
        painter.save()
        painter.setTransform(t_mat, combine=True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        painter.drawImage(src_rect, self._transform_source_qimage)
        painter.restore()

        # 2. Desenha a Bounding Box e as 8 Alças
        painter.save()
        zoom_factor = max(0.01, self.zoom)
        line_w = 1.2 / zoom_factor
        handle_sz = 8.0 / zoom_factor
        half_h = handle_sz / 2.0

        pen_box = QtGui.QPen(QtGui.QColor(0, 150, 255, 230), line_w)
        painter.setPen(pen_box)
        painter.setBrush(QtCore.Qt.NoBrush)

        c_tl = t_mat.map(src_rect.topLeft())
        c_tr = t_mat.map(src_rect.topRight())
        c_br = t_mat.map(src_rect.bottomRight())
        c_bl = t_mat.map(src_rect.bottomLeft())

        poly = QtGui.QPolygonF([c_tl, c_tr, c_br, c_bl])
        painter.drawPolygon(poly)

        c_tc = t_mat.map(QtCore.QPointF(src_rect.center().x(), src_rect.top()))
        c_bc = t_mat.map(QtCore.QPointF(src_rect.center().x(), src_rect.bottom()))
        c_ml = t_mat.map(QtCore.QPointF(src_rect.left(), src_rect.center().y()))
        c_mr = t_mat.map(QtCore.QPointF(src_rect.right(), src_rect.center().y()))

        handle_pen = QtGui.QPen(QtGui.QColor(0, 100, 200, 255), line_w)
        handle_brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 255))
        painter.setPen(handle_pen)
        painter.setBrush(handle_brush)

        for pt in (c_tl, c_tr, c_br, c_bl, c_tc, c_bc, c_ml, c_mr):
            painter.drawRect(QtCore.QRectF(pt.x() - half_h, pt.y() - half_h, handle_sz, handle_sz))

        # 3. Desenha o Pivô Central
        pv_mapped = t_mat.map(pv)
        pivot_r = 7.0 / zoom_factor
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 60, 60, 230), line_w * 1.5))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 180)))
        painter.drawEllipse(QtCore.QRectF(pv_mapped.x() - pivot_r, pv_mapped.y() - pivot_r, pivot_r * 2.0, pivot_r * 2.0))
        painter.drawLine(QtCore.QPointF(pv_mapped.x() - pivot_r - 2, pv_mapped.y()), QtCore.QPointF(pv_mapped.x() + pivot_r + 2, pv_mapped.y()))
        painter.drawLine(QtCore.QPointF(pv_mapped.x(), pv_mapped.y() - pivot_r - 2), QtCore.QPointF(pv_mapped.x(), pv_mapped.y() + pivot_r + 2))

        painter.restore()

    def _hit_test_transform_handle(self, canvas_pt: QtCore.QPointF) -> Optional[str]:
        if not self._transform_active:
            return None

        t_mat = self._get_transform_matrix()
        src_rect = self._transform_source_rect
        pv = self._transform_pivot
        zoom_factor = max(0.01, self.zoom)
        hit_dist = 12.0 / zoom_factor

        pv_mapped = t_mat.map(pv)
        if (canvas_pt - pv_mapped).manhattanLength() <= hit_dist:
            return "pivot"

        handles = {
            "tl": t_mat.map(src_rect.topLeft()),
            "tr": t_mat.map(src_rect.topRight()),
            "br": t_mat.map(src_rect.bottomRight()),
            "bl": t_mat.map(src_rect.bottomLeft()),
            "tc": t_mat.map(QtCore.QPointF(src_rect.center().x(), src_rect.top())),
            "bc": t_mat.map(QtCore.QPointF(src_rect.center().x(), src_rect.bottom())),
            "ml": t_mat.map(QtCore.QPointF(src_rect.left(), src_rect.center().y())),
            "mr": t_mat.map(QtCore.QPointF(src_rect.right(), src_rect.center().y())),
        }

        for h_name, h_pos in handles.items():
            if (canvas_pt - h_pos).manhattanLength() <= hit_dist:
                return h_name

        rot_dist = 30.0 / zoom_factor
        for h_name in ("tl", "tr", "br", "bl"):
            if (canvas_pt - handles[h_name]).manhattanLength() <= rot_dist:
                return "rotate"

        poly = QtGui.QPolygonF([handles["tl"], handles["tr"], handles["br"], handles["bl"]])
        if poly.containsPoint(canvas_pt, QtCore.Qt.OddEvenFill):
            return "move"

        return None

    def _update_transform_cursor(self, handle_name: Optional[str]):
        if handle_name == "move":
            self.setCursor(QtCore.Qt.SizeAllCursor)
        elif handle_name == "pivot":
            self.setCursor(QtCore.Qt.CrossCursor)
        elif handle_name == "rotate":
            self.setCursor(QtCore.Qt.PointingHandCursor)
        elif handle_name in ("tl", "br"):
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif handle_name in ("tr", "bl"):
            self.setCursor(QtCore.Qt.SizeBDiagCursor)
        elif handle_name in ("tc", "bc"):
            self.setCursor(QtCore.Qt.SizeVerCursor)
        elif handle_name in ("ml", "mr"):
            self.setCursor(QtCore.Qt.SizeHorCursor)
        else:
            self.unsetCursor()

    def _apply_transform_drag(self, canvas_pt: QtCore.QPointF, modifiers: QtCore.Qt.KeyboardModifiers):
        if not self._transform_active or not self._transform_handle_dragged or not self._transform_mouse_press_pos:
            return

        handle = self._transform_handle_dragged
        start_pt = self._transform_mouse_press_pos
        init_p = self._transform_press_params
        is_shift = bool(modifiers & QtCore.Qt.ShiftModifier)
        is_alt = bool(modifiers & QtCore.Qt.AltModifier)

        if handle == "move":
            self._transform_dx = init_p["dx"] + (canvas_pt.x() - start_pt.x())
            self._transform_dy = init_p["dy"] + (canvas_pt.y() - start_pt.y())

        elif handle == "pivot":
            self._transform_pivot = canvas_pt

        elif handle == "rotate":
            pv = self._transform_pivot
            pv_map = QtCore.QPointF(pv.x() + self._transform_dx, pv.y() + self._transform_dy)
            ang1 = math.atan2(start_pt.y() - pv_map.y(), start_pt.x() - pv_map.x())
            ang2 = math.atan2(canvas_pt.y() - pv_map.y(), canvas_pt.x() - pv_map.x())
            d_deg = math.degrees(ang2 - ang1)
            raw_rot = init_p["rot"] + d_deg
            if is_shift:
                self._transform_rotation = round(raw_rot / 15.0) * 15.0
            else:
                self._transform_rotation = raw_rot

        elif handle in ("tl", "tr", "bl", "br", "tc", "bc", "ml", "mr"):
            src_rect = self._transform_source_rect
            if src_rect.width() <= 0 or src_rect.height() <= 0:
                return

            pv = self._transform_pivot
            pv_map = QtCore.QPointF(pv.x() + self._transform_dx, pv.y() + self._transform_dy)
            
            rad = math.radians(self._transform_rotation)
            cosR = math.cos(-rad)
            sinR = math.sin(-rad)

            d_cur = canvas_pt - pv_map
            d_start = start_pt - pv_map

            # Projeção no sistema de coordenadas local
            cur_lx = d_cur.x() * cosR - d_cur.y() * sinR
            cur_ly = d_cur.x() * sinR + d_cur.y() * cosR

            start_lx = d_start.x() * cosR - d_start.y() * sinR
            start_ly = d_start.x() * sinR + d_start.y() * cosR

            factor_x = 1.0 if abs(start_lx) < 1e-4 else (cur_lx / start_lx)
            factor_y = 1.0 if abs(start_ly) < 1e-4 else (cur_ly / start_ly)

            if handle in ("tl", "tr", "bl", "br"):
                if is_shift or getattr(self, "_transform_lock_aspect", False):
                    avg = (abs(factor_x) + abs(factor_y)) / 2.0
                    factor_x = avg * (1.0 if factor_x >= 0 else -1.0)
                    factor_y = avg * (1.0 if factor_y >= 0 else -1.0)
                self._transform_scale_x = max(0.01, abs(init_p["sx"] * factor_x))
                self._transform_scale_y = max(0.01, abs(init_p["sy"] * factor_y))
            elif handle in ("ml", "mr"):
                self._transform_scale_x = max(0.01, abs(init_p["sx"] * factor_x))
            elif handle in ("tc", "bc"):
                self._transform_scale_y = max(0.01, abs(init_p["sy"] * factor_y))

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

        # 2. Ativação do Balde de Tinta (Ferramenta bucket)
        if event.button() == QtCore.Qt.LeftButton and self.active_tool == "bucket":
            self.do_flood_fill(event.position().x(), event.position().y())
            return

        # 3. Ativação da Varinha Mágica (Ferramenta wand)
        if event.button() == QtCore.Qt.LeftButton and self.active_tool == "wand":
            self.do_magic_wand_select(event.position().x(), event.position().y())
            return

        # 4. Ativação de Seleções Geométricas (rect_select / ellipse_select)
        if event.button() == QtCore.Qt.LeftButton and self.active_tool in ("rect_select", "ellipse_select"):
            world_evt = self.to_canvas(event.position().x(), event.position().y(), 1.0, 0.0)
            self._sel_drag_active = True
            self._sel_drag_start = QtCore.QPointF(world_evt.x, world_evt.y)
            self._sel_drag_current = self._sel_drag_start
            self.update()
            return

        # 5. Ativação do Laço de Seleção (lasso)
        if self.active_tool == "lasso":
            world_evt = self.to_canvas(event.position().x(), event.position().y(), 1.0, 0.0)
            pt = QtCore.QPointF(world_evt.x, world_evt.y)
            ltype = self._lasso_settings.get("lasso_type", "freehand")
            if ltype == "freehand" and event.button() == QtCore.Qt.LeftButton:
                self._lasso_is_drawing = True
                self._lasso_points = [pt]
                self.update()
                return
            elif ltype == "polygonal":
                if event.button() == QtCore.Qt.LeftButton:
                    if self._lasso_points and (pt - self._lasso_points[0]).manhattanLength() < max(6.0, 12.0 / max(0.01, self.zoom)) and len(self._lasso_points) >= 3:
                        self._finish_lasso_selection()
                    else:
                        self._lasso_points.append(pt)
                    self.update()
                    return
                elif event.button() == QtCore.Qt.RightButton:
                    self._lasso_points.clear()
                    self._lasso_hover_pt = None
                    self.update()
                    return

        # 6. Ativação / Interação da Ferramenta de Transformação (transform)
        if self.active_tool == "transform" or getattr(self, "_transform_active", False):
            if event.button() == QtCore.Qt.LeftButton:
                world_evt = self.to_canvas(event.position().x(), event.position().y(), 1.0, 0.0)
                pt = QtCore.QPointF(world_evt.x, world_evt.y)
                if getattr(self, "_transform_active", False):
                    handle = self._hit_test_transform_handle(pt)
                    if handle:
                        self._transform_handle_dragged = handle
                        self._transform_mouse_press_pos = pt
                        self._transform_press_params = {
                            "dx": self._transform_dx,
                            "dy": self._transform_dy,
                            "sx": self._transform_scale_x,
                            "sy": self._transform_scale_y,
                            "rot": self._transform_rotation,
                            "pivot": QtCore.QPointF(self._transform_pivot)
                        }
                        self.update()
                        return
                else:
                    self.start_transform_mode()
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

        # Interação / Arrasto de Transformação ativa
        if getattr(self, "_transform_active", False):
            world_evt = self.to_canvas(event.position().x(), event.position().y(), 1.0, 0.0)
            pt = QtCore.QPointF(world_evt.x, world_evt.y)
            if self._transform_handle_dragged:
                self._apply_transform_drag(pt, QtWidgets.QApplication.keyboardModifiers())
                self.update()
                return
            else:
                handle = self._hit_test_transform_handle(pt)
                self._update_transform_cursor(handle)

        # Arraste com Conta-Gotas ativo
        if self._eyedropper_active:
            self._eyedropper_pos = event.position()
            self._do_eyedrop_sample(event.position().x(), event.position().y())
            self.update()
            return

        # Arraste de Seleção Geométrica ativa
        if self._sel_drag_active:
            world_evt = self.to_canvas(event.position().x(), event.position().y(), 1.0, 0.0)
            self._sel_drag_current = QtCore.QPointF(world_evt.x, world_evt.y)
            self.update()
            return

        # Desenho / Rastro de Laço
        if self.active_tool == "lasso":
            world_evt = self.to_canvas(event.position().x(), event.position().y(), 1.0, 0.0)
            pt = QtCore.QPointF(world_evt.x, world_evt.y)
            if self._lasso_is_drawing:
                if not self._lasso_points or (pt - self._lasso_points[-1]).manhattanLength() >= 2.0:
                    self._lasso_points.append(pt)
                    self.update()
                return
            elif self._lasso_settings.get("lasso_type") == "polygonal" and self._lasso_points:
                self._lasso_hover_pt = pt
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

        if getattr(self, "_transform_active", False) and self._transform_handle_dragged and event.button() == QtCore.Qt.LeftButton:
            self._transform_handle_dragged = None
            self._transform_mouse_press_pos = None
            self.unsetCursor()
            self.update()
            return

        if self._eyedropper_active and event.button() == QtCore.Qt.LeftButton:
            self._eyedropper_active = False
            self.update()
            return

        if self._sel_drag_active and event.button() == QtCore.Qt.LeftButton:
            self._sel_drag_active = False
            self._finish_geom_selection()
            return

        if self.active_tool == "lasso" and self._lasso_is_drawing and event.button() == QtCore.Qt.LeftButton:
            self._lasso_is_drawing = False
            self._finish_lasso_selection()
            return

        if event.button() == QtCore.Qt.LeftButton and self.drawing:
            self.end_stroke(event.position().x(), event.position().y())
        elif event.button() in (QtCore.Qt.MiddleButton, QtCore.Qt.LeftButton):
            self.is_panning = False

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton and self.active_tool == "lasso" and self._lasso_points:
            self._finish_lasso_selection()
            return
        super().mouseDoubleClickEvent(event)

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

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        modifiers = event.modifiers()
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()

        if getattr(self, "_transform_active", False):
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                self.commit_transform()
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key_Escape:
                self.cancel_transform()
                event.accept()
                return
            elif event.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right, QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
                step = 10.0 if (modifiers & QtCore.Qt.ShiftModifier) else 1.0
                if event.key() == QtCore.Qt.Key_Left:
                    self._transform_dx -= step
                elif event.key() == QtCore.Qt.Key_Right:
                    self._transform_dx += step
                elif event.key() == QtCore.Qt.Key_Up:
                    self._transform_dy -= step
                elif event.key() == QtCore.Qt.Key_Down:
                    self._transform_dy += step
                self.update()
                event.accept()
                return

        if modifiers & QtCore.Qt.ControlModifier:
            if event.key() == QtCore.Qt.Key_T:
                # Ctrl+T -> Iniciar Transformação Livre
                self.start_transform_mode()
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key_D:
                # Ctrl+D -> Desmarcar Seleção
                if backend and hasattr(backend, "clear_selection"):
                    backend.clear_selection()
                    if hasattr(self, "_selection_timer"):
                        self._selection_timer.stop()
                    self.update()
                    event.accept()
                    return
            elif event.key() == QtCore.Qt.Key_I and (modifiers & QtCore.Qt.ShiftModifier):
                # Ctrl+Shift+I -> Inverter Seleção
                if backend and hasattr(backend, "invert_selection"):
                    backend.invert_selection()
                    if hasattr(self, "_selection_timer") and backend.has_selection():
                        self._selection_timer.start()
                    self.update()
                    event.accept()
                    return
            elif event.key() == QtCore.Qt.Key_A:
                # Ctrl+A -> Selecionar Tudo
                if backend and hasattr(backend, "select_all"):
                    backend.select_all()
                    if hasattr(self, "_selection_timer"):
                        self._selection_timer.start()
                    self.update()
                    event.accept()
                    return

        if event.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            # Delete / Backspace -> Apaga conteúdo da camada ativa dentro da seleção
            if backend and hasattr(backend, "has_selection") and backend.has_selection():
                if hasattr(backend, "delete_selection_on_active_layer"):
                    ok = backend.delete_selection_on_active_layer()
                    if ok:
                        self.update()
                        self.strokeFinished.emit()
                        event.accept()
                        return

        super().keyPressEvent(event)
