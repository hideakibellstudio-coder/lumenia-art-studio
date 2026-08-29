from PySide6 import QtWidgets, QtCore, QtGui
import math
from .components.navigator_preview import IconButton, NavigatorPreview


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

        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)

        from ui.core.widgets.card_box import PanelCardBox
        card_box = PanelCardBox("", content_inner, self)
        main_layout.addWidget(card_box)


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
