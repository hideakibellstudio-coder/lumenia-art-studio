from PySide6 import QtWidgets, QtCore, QtGui
import math

class IconButton(QtWidgets.QToolButton):
    def __init__(self, icon_name, tooltip="", parent=None, size=28, icon_size=18, checkable=False, icon_color=None):
        super().__init__(parent)
        self.setProperty("icon_name", icon_name)
        if icon_name:
            from ui.core.icons import get_icon
            self.setIcon(get_icon(icon_name, icon_color))
            
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setAutoRaise(True)
        if checkable: 
            self.setCheckable(True)


class NavigatorPreview(QtWidgets.QWidget):
    panRequested = QtCore.Signal(float, float)
    zoomRequested = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setStyleSheet("NavigatorPreview { background-color: transparent; }")
        
        # Default design colors
        self._color_paper = QtGui.QColor("#ffffff")
        self._color_border = QtGui.QColor("#334155")
        self._color_accent = QtGui.QColor("#3b82f6")
        self._color_canvas_bg = QtGui.QColor("#e2e8f0")
        self._color_empty_bg = QtGui.QColor("#262626")
        
        self.zoom_level = 1.0 
        self.cam_x = 0.5 
        self.cam_y = 0.5
        self.rotation = 0.0
        self.flip_x = False
        self.flip_y = False
        self.ratio_w = 1.0
        self.ratio_h = 1.0
        self.aspect_ratio = 1920.0 / 1080.0 # Canvas Aspect Ratio
        
        self.has_document = False
        self.artwork_pix = None
        self._is_dragging = False
        self._drag_offset = QtCore.QPointF(0, 0)
        
        # Load theme colors
        self.update_theme()
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self.update_theme)

    def update_theme(self, theme_name=None):
        from ui.core.theme.manager import ThemeManager
        theme = ThemeManager.instance()._themes.get(ThemeManager.instance().current_theme, {})
        colors = theme.get("colors", {})
        
        self._color_border = QtGui.QColor(ThemeManager.instance().resolve_color("BORDER", colors))
        self._color_accent = QtGui.QColor(ThemeManager.instance().resolve_color("ACCENT", colors))
        self._color_canvas_bg = QtGui.QColor(ThemeManager.instance().resolve_color("BG_LIGHT", colors))
        self._color_empty_bg = QtGui.QColor(ThemeManager.instance().resolve_color("bg_panel", colors))
        self.update()

    def set_artwork(self, pix):
        if isinstance(pix, QtGui.QImage):
            self.artwork_pix = QtGui.QPixmap.fromImage(pix)
        elif isinstance(pix, QtGui.QPixmap):
            self.artwork_pix = pix
        else:
            self.artwork_pix = None
        self.update()

    def update_state(self, zoom, x, y, rotation, flip_x, flip_y, ratio_w=1.0, ratio_h=1.0):
        self.zoom_level = zoom
        self.cam_x = x
        self.cam_y = y
        self.rotation = rotation
        self.flip_x = flip_x
        self.flip_y = flip_y
        self.ratio_w = ratio_w
        self.ratio_h = ratio_h
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        if not self.has_document:
            p.setBrush(self._color_empty_bg)
            p.setPen(QtCore.Qt.NoPen)
            p.drawRect(self.rect())
            p.end()
            return
            
        # Fit Document into Widget (aspect ratio)
        rect = self.rect()
        margin = 10
        avail_w = rect.width() - margin * 2
        avail_h = rect.height() - margin * 2
        
        if avail_w <= 0 or avail_h <= 0:
            p.end()
            return
            
        draw_w = avail_w
        draw_h = draw_w / self.aspect_ratio
        
        if draw_h > avail_h:
            draw_h = avail_h
            draw_w = draw_h * self.aspect_ratio
            
        ox = margin + (avail_w - draw_w) / 2
        oy = margin + (avail_h - draw_h) / 2
        
        self.draw_rect = QtCore.QRectF(ox, oy, draw_w, draw_h)
        
        # Draw Thumbnail Base (Paper)
        p.setBrush(self._color_paper)
        p.setPen(QtGui.QPen(self._color_border, 1))
        p.drawRect(self.draw_rect)
        
        # Draw Real Artwork Pixmap or Checkerboard Fallback
        if self.artwork_pix and not self.artwork_pix.isNull():
            p.drawPixmap(self.draw_rect.toRect(), self.artwork_pix)
        else:
            p.setBrush(self._color_canvas_bg)
            p.setPen(QtCore.Qt.NoPen)
            p.drawRect(self.draw_rect.adjusted(2, 2, -2, -2))
        
        # --- VIEWPORT RECTANGLE ---
        if self.has_document:
            # Calculate Viewport Size
            vw = draw_w * self.ratio_w
            vh = draw_h * self.ratio_h
            
            # Center of Viewport on Thumbnail
            tx = ox + self.cam_x * draw_w
            ty = oy + self.cam_y * draw_h
            
            p.save()
            p.translate(tx, ty)
            p.rotate(-self.rotation)
            
            sx = -1 if self.flip_x else 1
            sy = -1 if self.flip_y else 1
            p.scale(sx, sy)
            
            viewport_rect = QtCore.QRectF(-vw/2, -vh/2, vw, vh)
            self.viewport_rect = viewport_rect
            
            p.setPen(QtGui.QPen(self._color_accent, 2))
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawRect(viewport_rect)
            
            # Crosshair center
            p.setPen(QtGui.QPen(self._color_accent, 1, QtCore.Qt.DotLine))
            p.drawLine(QtCore.QPointF(-10, 0), QtCore.QPointF(10, 0))
            p.drawLine(QtCore.QPointF(0, -10), QtCore.QPointF(0, 10))
            
            p.restore()
        
        p.end()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.zoomRequested.emit(delta)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            local_pos = event.position()
            
            # Center of viewport in local coordinate space (translate tx, ty offset)
            if hasattr(self, 'draw_rect'):
                tx = self.draw_rect.x() + self.cam_x * self.draw_rect.width()
                ty = self.draw_rect.y() + self.cam_y * self.draw_rect.height()
                viewport_center = QtCore.QPointF(tx, ty)
                
                # Check if mouse clicked inside the viewport rect
                vw = self.draw_rect.width() * self.ratio_w
                vh = self.draw_rect.height() * self.ratio_h
                local_viewport_rect = QtCore.QRectF(tx - vw/2, ty - vh/2, vw, vh)
                
                if local_viewport_rect.contains(local_pos):
                    self._is_dragging = True
                    self._drag_offset = viewport_center - local_pos
                else:
                    self._is_dragging = True
                    self._drag_offset = QtCore.QPointF(0, 0)
                    self._handle_input(event.position())

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self._handle_input(event.position() + self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._is_dragging = False

    def _handle_input(self, local_pos):
        if not hasattr(self, 'draw_rect'): 
            return
        
        rel_x = local_pos.x() - self.draw_rect.x()
        rel_y = local_pos.y() - self.draw_rect.y()
        
        norm_x = max(0.0, min(1.0, rel_x / self.draw_rect.width()))
        norm_y = max(0.0, min(1.0, rel_y / self.draw_rect.height()))
        
        self.panRequested.emit(norm_x, norm_y)


class NavigatorControls(QtWidgets.QWidget):
    zoomChanged = QtCore.Signal(float)
    rotateChanged = QtCore.Signal(float)
    fitRequested = QtCore.Signal()
    flipHRequested = QtCore.Signal()
    flipVRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 4, 0, 4)
        main_layout.setSpacing(8)

        # --- ROW 1: ZOOM ---
        self.zoom_box = QtWidgets.QFrame()
        zoom_layout = QtWidgets.QVBoxLayout(self.zoom_box)
        zoom_layout.setContentsMargins(8, 8, 8, 8)
        zoom_layout.setSpacing(4)
        
        lbls_z = QtWidgets.QHBoxLayout()
        t_z = QtWidgets.QLabel("Zoom")
        t_z.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.lbl_zoom = QtWidgets.QLabel("100%")
        self.lbl_zoom.setAlignment(QtCore.Qt.AlignRight)
        self.lbl_zoom.setStyleSheet("font-size: 11px;")
        lbls_z.addWidget(t_z)
        lbls_z.addStretch()
        lbls_z.addWidget(self.lbl_zoom)
        
        self.slider_zoom = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_zoom.setRange(10, 1000) # Up to 1000%
        self.slider_zoom.setValue(100)
        self.slider_zoom.setCursor(QtCore.Qt.PointingHandCursor)
        self.slider_zoom.setFixedHeight(16)
        
        self.btn_z_minus = IconButton("zoom-out", "Zoom Out", size=22, icon_size=12)
        self.btn_z_plus = IconButton("zoom-in", "Zoom In", size=22, icon_size=12)
        self.btn_fit = IconButton("maximize", "Enquadrar Tela", size=22, icon_size=12)
        
        controls_z = QtWidgets.QHBoxLayout()
        controls_z.setSpacing(4)
        controls_z.addWidget(self.btn_z_minus)
        controls_z.addWidget(self.slider_zoom)
        controls_z.addWidget(self.btn_z_plus)
        controls_z.addWidget(self.btn_fit)
        
        zoom_layout.addLayout(lbls_z)
        zoom_layout.addLayout(controls_z)
        main_layout.addWidget(self.zoom_box)

        # --- ROW 2: ANGLE ---
        self.angle_box = QtWidgets.QFrame()
        angle_layout = QtWidgets.QVBoxLayout(self.angle_box)
        angle_layout.setContentsMargins(8, 8, 8, 8)
        angle_layout.setSpacing(4)
        
        lbls_r = QtWidgets.QHBoxLayout()
        t_r = QtWidgets.QLabel("Ângulo")
        t_r.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.lbl_angle = QtWidgets.QLabel("0°")
        self.lbl_angle.setAlignment(QtCore.Qt.AlignRight)
        self.lbl_angle.setStyleSheet("font-size: 11px;")
        lbls_r.addWidget(t_r)
        lbls_r.addStretch()
        lbls_r.addWidget(self.lbl_angle)
        
        self.slider_rot = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_rot.setRange(0, 360)
        self.slider_rot.setValue(0)
        self.slider_rot.setCursor(QtCore.Qt.PointingHandCursor)
        self.slider_rot.setFixedHeight(16)
        
        self.btn_reset = IconButton("refresh-ccw", "Resetar Rotação", size=22, icon_size=12)
        self.btn_fliph = IconButton("flip-horizontal", "Espelhar H", size=22, icon_size=12)
        self.btn_flipv = IconButton("flip-vertical", "Espelhar V", size=22, icon_size=12)
        
        controls_r = QtWidgets.QHBoxLayout()
        controls_r.setSpacing(4)
        controls_r.addWidget(self.btn_fliph)
        controls_r.addWidget(self.slider_rot)
        controls_r.addWidget(self.btn_flipv)
        controls_r.addWidget(self.btn_reset)
        
        angle_layout.addLayout(lbls_r)
        angle_layout.addLayout(controls_r)
        main_layout.addWidget(self.angle_box)
        
        # Connect Signals
        self.slider_zoom.valueChanged.connect(self._on_zoom_change)
        self.slider_rot.valueChanged.connect(self._on_rot_change)
        
        self.btn_z_minus.clicked.connect(lambda: self.slider_zoom.setValue(self.slider_zoom.value() - 10))
        self.btn_z_plus.clicked.connect(lambda: self.slider_zoom.setValue(self.slider_zoom.value() + 10))
        self.btn_fit.clicked.connect(self.fitRequested.emit)
        
        self.btn_reset.clicked.connect(lambda: self.slider_rot.setValue(0))
        self.btn_fliph.clicked.connect(self.flipVRequested.emit)
        self.btn_flipv.clicked.connect(self.flipHRequested.emit)

        # Style theme
        self.update_theme()
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self.update_theme)

    def update_theme(self, theme_name=None):
        from ui.core.theme.manager import ThemeManager
        border = ThemeManager.instance().get_color("border")
        bg_main = ThemeManager.instance().get_color("bg_main")
        text_main = ThemeManager.instance().get_color("text_main")
        
        style = f"""
            QFrame {{
                background-color: {bg_main};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QLabel {{
                border: none;
                background-color: transparent;
            }}
        """
        self.zoom_box.setStyleSheet(style)
        self.angle_box.setStyleSheet(style)
        
        from ui.core.icons import get_icon
        self.btn_z_minus.setIcon(get_icon("zoom-out", text_main))
        self.btn_z_plus.setIcon(get_icon("zoom-in", text_main))
        self.btn_fit.setIcon(get_icon("maximize", text_main))
        self.btn_reset.setIcon(get_icon("refresh-ccw", text_main))
        self.btn_fliph.setIcon(get_icon("flip-horizontal", text_main))
        self.btn_flipv.setIcon(get_icon("flip-vertical", text_main))

    def _on_zoom_change(self, val):
        self.lbl_zoom.setText(f"{val}%")
        self.zoomChanged.emit(val / 100.0)

    def _on_rot_change(self, val):
        self.lbl_angle.setText(f"{val}°")
        self.rotateChanged.emit(float(val))


class NavigatorPanel(QtWidgets.QWidget):
    camera_changed_by_user = QtCore.Signal(float, float, float, float) # zoom, norm_x, norm_y, rotation
    request_global_fit_view = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        
        self.state = {
            "zoom": 1.0,
            "rotation": 0.0,
            "pan_x": 0.5,
            "pan_y": 0.5,
            "flip_x": False,
            "flip_y": False,
            "ratio_w": 1.0,
            "ratio_h": 1.0
        }

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Components
        self.preview = NavigatorPreview()
        self.controls = NavigatorControls()

        # Build Box
        content_inner = QtWidgets.QWidget()
        c_layout = QtWidgets.QVBoxLayout(content_inner)
        c_layout.setContentsMargins(4, 4, 4, 4)
        c_layout.setSpacing(6)

        c_layout.addWidget(self.preview)
        c_layout.addWidget(self.controls)

        from ui.core.widgets.card_box import PanelCardBox
        card_box = PanelCardBox("🧭 Navegador", content_inner, self)

        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        scroll_content = QtWidgets.QWidget()
        sc_layout = QtWidgets.QVBoxLayout(scroll_content)
        sc_layout.setContentsMargins(10, 10, 10, 10)
        sc_layout.addWidget(card_box)
        sc_layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)


        # Connections
        self.controls.zoomChanged.connect(self.set_zoom)
        self.controls.rotateChanged.connect(self.set_rotation)
        self.controls.fitRequested.connect(self.fit_to_screen) 
        
        self.controls.flipHRequested.connect(self.toggle_flip_h)
        self.controls.flipVRequested.connect(self.toggle_flip_v)
        
        self.preview.panRequested.connect(self.set_pan)
        self.preview.zoomRequested.connect(self._on_wheel_zoom)

        self._refresh_all()

    def set_zoom(self, value):
        self.state["zoom"] = max(0.05, value)
        self.camera_changed_by_user.emit(self.state["zoom"], self.state["pan_x"], self.state["pan_y"], self.state["rotation"])

    def update_viewport(self, zoom, norm_x, norm_y, rot, fx, fy, ratio_w, ratio_h):
        self.state["zoom"] = zoom
        self.state["pan_x"] = norm_x
        self.state["pan_y"] = norm_y
        self.state["rotation"] = rot
        self.state["flip_x"] = bool(fx)
        self.state["flip_y"] = bool(fy)
        self.state["ratio_w"] = ratio_w
        self.state["ratio_h"] = ratio_h
        
        # update zoom slider without feedback loop
        self.controls.slider_zoom.blockSignals(True)
        z_val = int(zoom * 100)
        self.controls.slider_zoom.setValue(z_val)
        self.controls.lbl_zoom.setText(f"{z_val}%")
        self.controls.slider_zoom.blockSignals(False)
        
        # update rotation slider without feedback loop
        self.controls.slider_rot.blockSignals(True)
        r_val = int(rot)
        self.controls.slider_rot.setValue(r_val)
        self.controls.lbl_angle.setText(f"{r_val}°")
        self.controls.slider_rot.blockSignals(False)
        
        self._refresh_all()

    def set_rotation(self, degrees):
        self.state["rotation"] = degrees
        self._refresh_all()
        self.camera_changed_by_user.emit(self.state["zoom"], self.state["pan_x"], self.state["pan_y"], degrees)

    def set_pan(self, x, y):
        self.state["pan_x"] = x
        self.state["pan_y"] = y
        self._refresh_all()
        self.camera_changed_by_user.emit(self.state["zoom"], x, y, self.state["rotation"])

    def toggle_flip_h(self):
        self.state["flip_x"] = not self.state["flip_x"]
        self._refresh_all()

    def toggle_flip_v(self):
        self.state["flip_y"] = not self.state["flip_y"]
        self._refresh_all()

    def _on_wheel_zoom(self, delta):
        current_percent = int(self.state["zoom"] * 100)
        new_val = current_percent + 10 if delta > 0 else current_percent - 10
        new_val = max(10, min(1000, new_val))
        self.controls.slider_zoom.setValue(new_val)

    def fit_to_screen(self):
        self.request_global_fit_view.emit()

    def set_has_document(self, has_doc: bool):
        self.preview.has_document = has_doc
        self.preview.update()

    def set_artwork(self, pix):
        self.preview.set_artwork(pix)

    def _refresh_all(self):
        self.preview.update_state(
            self.state["zoom"], 
            self.state["pan_x"], 
            self.state["pan_y"],
            self.state["rotation"],
            self.state["flip_x"],
            self.state["flip_y"],
            self.state["ratio_w"],
            self.state["ratio_h"]
        )

    def set_has_document(self, has_doc):
        self.preview.has_document = has_doc
        self.controls.setEnabled(has_doc)
        self.preview.update()
