"""Advanced Settings Floating Window for Curvilinear 6P, Rulers and Symmetry."""

from PySide6 import QtWidgets, QtCore, QtGui


class AdvancedGeometryDialog(QtWidgets.QDialog):
    """Janela flutuante completa de configurações avançadas com rolagem e agrupamentos."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None, current_state=None):
        super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Configurações Avançadas de Geometria")
        self.setFixedSize(360, 600)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.state = current_state.copy() if current_state else {}
        self._drag_pos = None
        self._build_ui()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        frame = QtWidgets.QFrame()
        frame.setStyleSheet("""
            QFrame { background-color: #181825; border: 1px solid #45475a; border-radius: 8px; }
            QLabel { color: #cdd6f4; font-size: 11px; }
            QLabel.sec-title { color: #a855f7; font-weight: bold; font-size: 10px; margin-top: 6px; }
            QCheckBox { color: #cdd6f4; font-size: 11px; }
            QSlider::groove:horizontal { height: 4px; background: #313244; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #a855f7; border-radius: 2px; }
            QSlider::handle:horizontal { background: #cdd6f4; width: 12px; margin: -4px 0; border-radius: 6px; }
            QComboBox { background: #1e1e2e; color: #cdd6f4; border: 1px solid #313244; border-radius: 4px; padding: 3px 6px; }
            QPushButton { background: #313244; color: #cdd6f4; border-radius: 4px; padding: 5px 12px; font-weight: bold; font-size: 11px; }
            QPushButton:hover { background: #45475a; color: #ffffff; }
        """)
        f_layout = QtWidgets.QVBoxLayout(frame)
        f_layout.setContentsMargins(10, 8, 10, 10)
        f_layout.setSpacing(6)

        # Header
        hdr = QtWidgets.QHBoxLayout()
        lbl_title = QtWidgets.QLabel("⚙️ Configurações Avançadas de Geometria")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #a855f7;")
        btn_close = QtWidgets.QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.setStyleSheet("background: transparent; color: #6c7086; border: none; font-weight: bold; font-size: 13px;")
        btn_close.clicked.connect(self.close)
        hdr.addWidget(lbl_title)
        hdr.addStretch()
        hdr.addWidget(btn_close)
        f_layout.addLayout(hdr)

        # Scroll Area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QtWidgets.QWidget()
        c_lay = QtWidgets.QVBoxLayout(content)
        c_lay.setContentsMargins(4, 4, 4, 4)
        c_lay.setSpacing(8)

        # ── 1. PERSPECTIVA CURVILÍNEA 6P ──
        lbl_curv = QtWidgets.QLabel("🌐  PERSPECTIVA CURVILÍNEA (6 PONTOS)")
        lbl_curv.setProperty("class", "sec-title")
        c_lay.addWidget(lbl_curv)

        self.w_yaw, self.slider_yaw, self.lbl_yaw = self._make_slider("Rotação (Yaw):", 0, 360, "°", int(self.state.get("yaw", 0)))
        self.w_pitch, self.slider_pitch, self.lbl_pitch = self._make_slider("Inclinação (Pitch):", -90, 90, "°", int(self.state.get("pitch", 0)))
        self.w_fov, self.slider_fov, self.lbl_fov = self._make_slider("FOV (Distorção):", 10, 180, "°", int(self.state.get("fov", 130)))
        c_lay.addWidget(self.w_yaw)
        c_lay.addWidget(self.w_pitch)
        c_lay.addWidget(self.w_fov)

        row_density = QtWidgets.QHBoxLayout()
        row_density.addWidget(QtWidgets.QLabel("Densidade das Linhas:"))
        self.combo_density = QtWidgets.QComboBox()
        self.combo_density.addItems(["Fina (15°)", "Média (30°)", "Esparsa (45°)"])
        self.combo_density.setCurrentIndex(self.state.get("density_idx", 1))
        self.combo_density.currentIndexChanged.connect(self._on_changed)
        row_density.addWidget(self.combo_density)
        c_lay.addLayout(row_density)

        # 12-item Checkbox Grid
        grid_curv = QtWidgets.QGridLayout()
        grid_curv.setSpacing(4)
        self.chk_ring = QtWidgets.QCheckBox("Limites (180°)")
        self.chk_straight_v = QtWidgets.QCheckBox("Verticais Retas")
        self.chk_v = QtWidgets.QCheckBox("Grade Vertical (V)")
        self.chk_vps = QtWidgets.QCheckBox("Pontos Fuga (VPs)")
        self.chk_h = QtWidgets.QCheckBox("Grade Horiz. (H)")
        self.chk_letterbox = QtWidgets.QCheckBox("Letterbox")
        self.chk_d = QtWidgets.QCheckBox("Grade Prof. (D)")
        self.chk_cube = QtWidgets.QCheckBox("Cubo 3D")
        self.chk_ground = QtWidgets.QCheckBox("Grade Chão")
        self.chk_ceiling = QtWidgets.QCheckBox("Grade Teto")
        self.chk_ground_v = QtWidgets.QCheckBox("Verticais Chão")
        self.chk_ceiling_v = QtWidgets.QCheckBox("Verticais Teto")

        chk_items = [
            (self.chk_ring, "show_ring", True, 0, 0),
            (self.chk_straight_v, "show_straight_verticals", False, 0, 1),
            (self.chk_v, "show_v", True, 1, 0),
            (self.chk_vps, "show_vps", False, 1, 1),
            (self.chk_h, "show_h", True, 2, 0),
            (self.chk_letterbox, "show_letterbox", False, 2, 1),
            (self.chk_d, "show_d", True, 3, 0),
            (self.chk_cube, "show_cube", False, 3, 1),
            (self.chk_ground, "show_ground", False, 4, 0),
            (self.chk_ceiling, "show_ceiling", False, 4, 1),
            (self.chk_ground_v, "show_ground_verticals", False, 5, 0),
            (self.chk_ceiling_v, "show_ceiling_verticals", False, 5, 1),
        ]
        for chk, key, def_val, row, col in chk_items:
            chk.setChecked(self.state.get(key, def_val))
            chk.toggled.connect(self._on_changed)
            grid_curv.addWidget(chk, row, col)
        c_lay.addLayout(grid_curv)

        row_aspect = QtWidgets.QHBoxLayout()
        row_aspect.addWidget(QtWidgets.QLabel("Proporção do Viewport:"))
        self.combo_aspect = QtWidgets.QComboBox()
        self.combo_aspect.addItems(["16:9", "2.35:1"])
        self.combo_aspect.setCurrentText(self.state.get("aspect_ratio", "16:9"))
        self.combo_aspect.currentIndexChanged.connect(self._on_changed)
        row_aspect.addWidget(self.combo_aspect)
        c_lay.addLayout(row_aspect)

        # ── 2. DESENHO & SNAPPING ──
        lbl_snap = QtWidgets.QLabel("📏  DESENHO & SNAPPING (IMÃ)")
        lbl_snap.setProperty("class", "sec-title")
        c_lay.addWidget(lbl_snap)

        row_mode = QtWidgets.QHBoxLayout()
        row_mode.addWidget(QtWidgets.QLabel("Eixo de Snap:"))
        self.combo_snap_mode = QtWidgets.QComboBox()
        self.combo_snap_mode.addItems(["Auto (Todas as Guias)", "Apenas Vertical (V)", "Apenas Horizontal (H)", "Apenas Profundidade (D)"])
        mode_map = {"auto": 0, "v": 1, "h": 2, "d": 3}
        self.combo_snap_mode.setCurrentIndex(mode_map.get(self.state.get("snap_mode", "auto"), 0))
        self.combo_snap_mode.currentIndexChanged.connect(self._on_changed)
        row_mode.addWidget(self.combo_snap_mode)
        c_lay.addLayout(row_mode)

        self.w_sens, self.slider_sens, self.lbl_sens = self._make_slider("Sensibilidade do Snap:", 1, 50, " px", int(self.state.get("snap_sensitivity", 3)))
        c_lay.addWidget(self.w_sens)

        self.chk_dynamic = QtWidgets.QCheckBox("Ativar Snap Dinâmico (Desenho Livre)")
        self.chk_dynamic.setChecked(self.state.get("snap_dynamic", True))
        self.chk_dynamic.toggled.connect(self._on_changed)
        c_lay.addWidget(self.chk_dynamic)

        self.chk_hint = QtWidgets.QCheckBox("Exibir Guia Vermelha (Cursor Hint)")
        self.chk_hint.setChecked(self.state.get("show_hint", True))
        self.chk_hint.toggled.connect(self._on_changed)
        c_lay.addWidget(self.chk_hint)

        self.chk_hide = QtWidgets.QCheckBox("Ocultar guias visuais durante a pintura")
        self.chk_hide.setChecked(self.state.get("hidden", False))
        self.chk_hide.toggled.connect(self._on_changed)
        c_lay.addWidget(self.chk_hide)

        # ── 3. PARÂMETROS DE SIMETRIA ──
        lbl_sym = QtWidgets.QLabel("🪞  PARÂMETROS DE SIMETRIA")
        lbl_sym.setProperty("class", "sec-title")
        c_lay.addWidget(lbl_sym)

        row_seg = QtWidgets.QHBoxLayout()
        row_seg.addWidget(QtWidgets.QLabel("Segmentos Radiais:"))
        self.spin_seg = QtWidgets.QSpinBox()
        self.spin_seg.setRange(2, 32)
        self.spin_seg.setValue(self.state.get("segments", 6))
        self.spin_seg.valueChanged.connect(self._on_changed)
        row_seg.addWidget(self.spin_seg)
        c_lay.addLayout(row_seg)

        self.w_ang, self.slider_ang, self.lbl_ang = self._make_slider("Ângulo do Eixo:", 0, 360, "°", int(self.state.get("angle", 0)))
        c_lay.addWidget(self.w_ang)

        self.chk_stop = QtWidgets.QCheckBox("Parar traço no centro (Stop-at-Center)")
        self.chk_stop.setChecked(self.state.get("stop_at_center", False))
        self.chk_stop.toggled.connect(self._on_changed)
        c_lay.addWidget(self.chk_stop)

        self.chk_lock = QtWidgets.QCheckBox("Bloquear posição do centro no canvas")
        self.chk_lock.setChecked(self.state.get("locked", False))
        self.chk_lock.toggled.connect(self._on_changed)
        c_lay.addWidget(self.chk_lock)

        scroll.setWidget(content)
        f_layout.addWidget(scroll, 1)

        # Footer Buttons
        btn_reset = QtWidgets.QPushButton("Restaurar Padrões")
        btn_reset.clicked.connect(self._on_reset)
        f_layout.addWidget(btn_reset)

        main_layout.addWidget(frame)

    def _make_slider(self, text, min_v, max_v, suffix, cur_v):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel(text))
        lbl_v = QtWidgets.QLabel(f"{cur_v}{suffix}")
        lbl_v.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        top.addWidget(lbl_v, 0, QtCore.Qt.AlignRight)
        lay.addLayout(top)
        s = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        s.setRange(min_v, max_v)
        s.setValue(cur_v)
        s.valueChanged.connect(lambda v: (lbl_v.setText(f"{v}{suffix}"), self._on_changed()))
        lay.addWidget(s)
        return w, s, lbl_v

    def _on_changed(self):
        self.state["yaw"] = float(self.slider_yaw.value())
        self.state["pitch"] = float(self.slider_pitch.value())
        self.state["fov"] = float(self.slider_fov.value())
        self.state["density_idx"] = self.combo_density.currentIndex()
        density_map = {0: 15.0, 1: 30.0, 2: 45.0}
        self.state["density"] = density_map.get(self.combo_density.currentIndex(), 30.0)

        self.state["show_ring"] = self.chk_ring.isChecked()
        self.state["show_straight_verticals"] = self.chk_straight_v.isChecked()
        self.state["show_v"] = self.chk_v.isChecked()
        self.state["show_vps"] = self.chk_vps.isChecked()
        self.state["show_h"] = self.chk_h.isChecked()
        self.state["show_letterbox"] = self.chk_letterbox.isChecked()
        self.state["show_d"] = self.chk_d.isChecked()
        self.state["show_cube"] = self.chk_cube.isChecked()
        self.state["show_ground"] = self.chk_ground.isChecked()
        self.state["show_ceiling"] = self.chk_ceiling.isChecked()
        self.state["show_ground_verticals"] = self.chk_ground_v.isChecked()
        self.state["show_ceiling_verticals"] = self.chk_ceiling_v.isChecked()
        self.state["aspect_ratio"] = self.combo_aspect.currentText()

        mode_inv = {0: "auto", 1: "v", 2: "h", 3: "d"}
        self.state["snap_mode"] = mode_inv.get(self.combo_snap_mode.currentIndex(), "auto")
        self.state["snap_sensitivity"] = float(self.slider_sens.value())
        self.state["snap_dynamic"] = self.chk_dynamic.isChecked()
        self.state["show_hint"] = self.chk_hint.isChecked()
        self.state["hidden"] = self.chk_hide.isChecked()

        self.state["segments"] = self.spin_seg.value()
        self.state["angle"] = float(self.slider_ang.value())
        self.state["stop_at_center"] = self.chk_stop.isChecked()
        self.state["locked"] = self.chk_lock.isChecked()

        self.settingsChanged.emit(self.state)

    def _on_reset(self):
        self.slider_yaw.setValue(0)
        self.slider_pitch.setValue(0)
        self.slider_fov.setValue(130)
        self.combo_density.setCurrentIndex(1)
        self.chk_ring.setChecked(True)
        self.chk_straight_v.setChecked(False)
        self.chk_v.setChecked(True)
        self.chk_vps.setChecked(False)
        self.chk_h.setChecked(True)
        self.chk_letterbox.setChecked(False)
        self.chk_d.setChecked(True)
        self.chk_cube.setChecked(False)
        self.chk_ground.setChecked(False)
        self.chk_ceiling.setChecked(False)
        self.chk_ground_v.setChecked(False)
        self.chk_ceiling_v.setChecked(False)
        self.combo_aspect.setCurrentText("16:9")
        self.combo_snap_mode.setCurrentIndex(0)
        self.slider_sens.setValue(3)
        self.chk_dynamic.setChecked(True)
        self.chk_hint.setChecked(True)
        self.chk_hide.setChecked(False)
        self.spin_seg.setValue(6)
        self.slider_ang.setValue(0)
        self.chk_stop.setChecked(False)
        self.chk_lock.setChecked(False)

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == QtCore.Qt.LeftButton and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _):
        self._drag_pos = None
