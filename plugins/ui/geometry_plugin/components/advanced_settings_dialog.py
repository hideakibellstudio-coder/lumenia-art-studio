"""Advanced Geometry Dialog padronizado no Design System do Lumenia V2."""

from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon
from plugins.ui.brush_plugin.compact_slider import CompactSlider
from plugins.ui.brush_plugin.collapsible_section import CollapsibleSection


class AdvancedGeometryDialog(QtWidgets.QDialog):
    """Janela flutuante avançada padronizada com abas, aberturas colapsáveis e sliders compactos."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None, current_state=None):
        flags = QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint
        super().__init__(parent, flags)
        self.setWindowTitle("Configurações Avançadas de Geometria")
        self.setMinimumWidth(330)
        self.setMinimumHeight(460)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.state = current_state.copy() if current_state else {}
        self._drag_pos = None
        self._build_ui()

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme("")

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & QtCore.Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def show_near(self, anchor_widget: QtWidgets.QWidget):
        curr = anchor_widget
        workspace, left_dock, right_dock = None, None, None
        while curr:
            if hasattr(curr, "workspace_area"):
                workspace = curr
                left_dock = getattr(curr, "left_dock", None)
                right_dock = getattr(curr, "right_dock", None)
                break
            curr = curr.parentWidget()

        scr = anchor_widget.screen().availableGeometry() if anchor_widget.screen() else QtCore.QRect(0, 0, 1920, 1080)
        anchor_global = anchor_widget.mapToGlobal(QtCore.QPoint(0, 0))
        is_on_right = anchor_global.x() > scr.center().x()

        if workspace and (right_dock or left_dock):
            workspace_global = workspace.workspace_area.mapToGlobal(QtCore.QPoint(0, 0))
            target_h = max(440, workspace.workspace_area.height() - 20)
            y = workspace_global.y() + 10

            if is_on_right and right_dock:
                dock_left = right_dock.mapToGlobal(QtCore.QPoint(0, 0)).x()
                if hasattr(right_dock, "drawer_container") and right_dock.drawer_container.isVisible():
                    drawer_left = right_dock.drawer_container.mapToGlobal(QtCore.QPoint(0, 0)).x()
                    dock_left = min(dock_left, drawer_left)
                x = dock_left - self.width() - 10
            elif left_dock:
                dock_right = left_dock.mapToGlobal(QtCore.QPoint(left_dock.width(), 0)).x()
                if hasattr(left_dock, "drawer_container") and left_dock.drawer_container.isVisible():
                    drawer_right = left_dock.drawer_container.mapToGlobal(QtCore.QPoint(left_dock.drawer_container.width(), 0)).x()
                    dock_right = max(dock_right, drawer_right)
                x = dock_right + 10
            else:
                x = anchor_global.x() - self.width() - 10 if is_on_right else anchor_global.x() + anchor_widget.width() + 10
        else:
            x = anchor_global.x() - self.width() - 10 if is_on_right else anchor_global.x() + anchor_widget.width() + 10
            y = anchor_global.y()
            target_h = 520

        if x < scr.left() + 10:
            x = scr.left() + 10
        elif x + self.width() > scr.right() - 10:
            x = scr.right() - self.width() - 10

        self.setFixedHeight(min(target_h, scr.height() - 40))
        if y + self.height() > scr.bottom():
            y = max(scr.top() + 10, scr.bottom() - self.height() - 10)

        self.move(QtCore.QPoint(x, y))
        self.show()
        self.raise_()
        self.activateWindow()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.container = QtWidgets.QWidget()
        self.container.setObjectName("AdvContainer")
        main_layout.addWidget(self.container)

        outer = QtWidgets.QVBoxLayout(self.container)
        outer.setContentsMargins(1, 0, 1, 1)
        outer.setSpacing(0)

        outer.addWidget(self._make_title_bar())
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setObjectName("AdvSep")
        outer.addWidget(sep)

        self.tab_bar = QtWidgets.QTabBar()
        self.tab_bar.setExpanding(True)
        self.tab_bar.addTab("Perspectiva 6P")
        self.tab_bar.addTab("Snapping && Guias")
        self.tab_bar.addTab("Simetria")
        self.tab_bar.setObjectName("AdvTabBar")
        self.tab_bar.currentChanged.connect(self._on_tab)

        tab_wrap = QtWidgets.QWidget()
        tab_wrap.setObjectName("AdvTabWrap")
        tw = QtWidgets.QHBoxLayout(tab_wrap)
        tw.setContentsMargins(8, 6, 8, 0)
        tw.addWidget(self.tab_bar, 1)
        outer.addWidget(tab_wrap)

        self.stack = QtWidgets.QStackedWidget()
        outer.addWidget(self.stack, 1)

        self.stack.addWidget(self._build_curv_page())
        self.stack.addWidget(self._build_snap_page())
        self.stack.addWidget(self._build_sym_page())

        footer = QtWidgets.QWidget()
        fl = QtWidgets.QHBoxLayout(footer)
        fl.setContentsMargins(8, 4, 8, 8)
        self.btn_reset = QtWidgets.QPushButton("Restaurar Padrões")
        self.btn_reset.setObjectName("AdvResetBtn")
        self.btn_reset.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._on_reset)
        fl.addWidget(self.btn_reset)
        outer.addWidget(footer)

    def _make_title_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setObjectName("AdvTitleBar")
        bar.setFixedHeight(34)
        lo = QtWidgets.QHBoxLayout(bar)
        lo.setContentsMargins(10, 0, 8, 0)
        lo.setSpacing(6)

        icon = QtWidgets.QLabel()
        icon.setObjectName("AdvTitleIcon")
        icon.setFixedSize(16, 16)
        icon.setPixmap(get_icon("settings").pixmap(QtCore.QSize(14, 14)))

        title = QtWidgets.QLabel("CONFIGURAÇÕES AVANÇADAS DE GEOMETRIA")
        title.setObjectName("AdvTitleLabel")

        self.btn_close = QtWidgets.QToolButton()
        self.btn_close.setObjectName("AdvCloseBtn")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setIconSize(QtCore.QSize(12, 12))
        self.btn_close.setIcon(get_icon("close"))
        self.btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide)

        lo.addWidget(icon)
        lo.addWidget(title)
        lo.addStretch()
        lo.addWidget(self.btn_close)
        return bar

    def _build_curv_page(self) -> QtWidgets.QWidget:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        content = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(content)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(6)

        sec_cam = CollapsibleSection("CÂMERA 3D & DISTORÇÃO", content)
        self.slider_yaw = CompactSlider("Yaw:", 0, 360, "°", sec_cam, step=5)
        self.slider_yaw.setValue(int(self.state.get("yaw", 0)))
        self.slider_yaw.valueChanged.connect(self._on_changed)
        sec_cam.add_widget(self.slider_yaw)

        self.slider_pitch = CompactSlider("Pitch:", -90, 90, "°", sec_cam, step=5)
        self.slider_pitch.setValue(int(self.state.get("pitch", 0)))
        self.slider_pitch.valueChanged.connect(self._on_changed)
        sec_cam.add_widget(self.slider_pitch)

        self.slider_fov = CompactSlider("FOV:", 10, 180, "°", sec_cam, step=5)
        self.slider_fov.setValue(int(self.state.get("fov", 130)))
        self.slider_fov.valueChanged.connect(self._on_changed)
        sec_cam.add_widget(self.slider_fov)
        lay.addWidget(sec_cam)

        sec_grid = CollapsibleSection("GRADE CURVILÍNEA & ELEMENTOS", content)
        row_d = QtWidgets.QHBoxLayout()
        lbl_d = QtWidgets.QLabel("Densidade:")
        lbl_d.setObjectName("AdvFieldLabel")
        row_d.addWidget(lbl_d)
        self.combo_density = QtWidgets.QComboBox()
        self.combo_density.addItems(["Fina (15°)", "Média (30°)", "Esparsa (45°)"])
        self.combo_density.setCurrentIndex(self.state.get("density_idx", 1))
        self.combo_density.currentIndexChanged.connect(self._on_changed)
        row_d.addWidget(self.combo_density, 1)
        sec_grid.add_layout(row_d)

        row_a = QtWidgets.QHBoxLayout()
        lbl_a = QtWidgets.QLabel("Proporção:")
        lbl_a.setObjectName("AdvFieldLabel")
        row_a.addWidget(lbl_a)
        self.combo_aspect = QtWidgets.QComboBox()
        self.combo_aspect.addItems(["16:9", "2.35:1"])
        self.combo_aspect.setCurrentText(self.state.get("aspect_ratio", "16:9"))
        self.combo_aspect.currentIndexChanged.connect(self._on_changed)
        row_a.addWidget(self.combo_aspect, 1)
        sec_grid.add_layout(row_a)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(4)
        self.chk_ring = QtWidgets.QCheckBox("Limites (180°)")
        self.chk_straight_v = QtWidgets.QCheckBox("Verticais Retas")
        self.chk_v = QtWidgets.QCheckBox("Grade Vert. (V)")
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
            (self.chk_ring, "show_ring", True, 0, 0), (self.chk_straight_v, "show_straight_verticals", False, 0, 1),
            (self.chk_v, "show_v", True, 1, 0), (self.chk_vps, "show_vps", False, 1, 1),
            (self.chk_h, "show_h", True, 2, 0), (self.chk_letterbox, "show_letterbox", False, 2, 1),
            (self.chk_d, "show_d", True, 3, 0), (self.chk_cube, "show_cube", False, 3, 1),
            (self.chk_ground, "show_ground", False, 4, 0), (self.chk_ceiling, "show_ceiling", False, 4, 1),
            (self.chk_ground_v, "show_ground_verticals", False, 5, 0), (self.chk_ceiling_v, "show_ceiling_verticals", False, 5, 1),
        ]
        for chk, key, def_val, r, c in chk_items:
            chk.setChecked(self.state.get(key, def_val))
            chk.toggled.connect(self._on_changed)
            grid.addWidget(chk, r, c)
        sec_grid.add_layout(grid)
        lay.addWidget(sec_grid)
        lay.addStretch()

        scroll.setWidget(content)
        return scroll

    def _build_snap_page(self) -> QtWidgets.QWidget:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        content = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(content)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(6)

        sec_snap = CollapsibleSection("MODO & SENSIBILIDADE", content)
        row_m = QtWidgets.QHBoxLayout()
        lbl_m = QtWidgets.QLabel("Eixo de Snap:")
        lbl_m.setObjectName("AdvFieldLabel")
        row_m.addWidget(lbl_m)
        self.combo_snap_mode = QtWidgets.QComboBox()
        self.combo_snap_mode.addItems(["Auto (Todas as Guias)", "Apenas Vertical (V)", "Apenas Horizontal (H)", "Apenas Profundidade (D)"])
        mode_map = {"auto": 0, "v": 1, "h": 2, "d": 3}
        self.combo_snap_mode.setCurrentIndex(mode_map.get(self.state.get("snap_mode", "auto"), 0))
        self.combo_snap_mode.currentIndexChanged.connect(self._on_changed)
        row_m.addWidget(self.combo_snap_mode, 1)
        sec_snap.add_layout(row_m)

        self.slider_sens = CompactSlider("Sensib:", 1, 50, "px", sec_snap)
        self.slider_sens.setValue(int(self.state.get("snap_sensitivity", 3)))
        self.slider_sens.valueChanged.connect(self._on_changed)
        sec_snap.add_widget(self.slider_sens)
        lay.addWidget(sec_snap)

        sec_draw = CollapsibleSection("COMPORTAMENTO DE DESENHO", content)
        self.chk_dynamic = QtWidgets.QCheckBox("Ativar Snap Dinâmico (Desenho Livre)")
        self.chk_dynamic.setChecked(self.state.get("snap_dynamic", True))
        self.chk_dynamic.toggled.connect(self._on_changed)
        sec_draw.add_widget(self.chk_dynamic)

        self.chk_hint = QtWidgets.QCheckBox("Exibir Guia Cursor Hint (Laranja)")
        self.chk_hint.setChecked(self.state.get("show_hint", True))
        self.chk_hint.toggled.connect(self._on_changed)
        sec_draw.add_widget(self.chk_hint)

        self.chk_hide = QtWidgets.QCheckBox("Ocultar guias visuais durante a pintura")
        self.chk_hide.setChecked(self.state.get("hidden", False))
        self.chk_hide.toggled.connect(self._on_changed)
        sec_draw.add_widget(self.chk_hide)
        lay.addWidget(sec_draw)
        lay.addStretch()

        scroll.setWidget(content)
        return scroll

    def _build_sym_page(self) -> QtWidgets.QWidget:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        content = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(content)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(6)

        sec_axes = CollapsibleSection("EIXOS & ÂNGULO", content)
        self.slider_seg = CompactSlider("Segmentos:", 2, 32, "", sec_axes)
        self.slider_seg.setValue(int(self.state.get("segments", 6)))
        self.slider_seg.valueChanged.connect(self._on_changed)
        sec_axes.add_widget(self.slider_seg)

        self.slider_ang = CompactSlider("Ângulo:", 0, 360, "°", sec_axes, step=5)
        self.slider_ang.setValue(int(self.state.get("angle", 0)))
        self.slider_ang.valueChanged.connect(self._on_changed)
        sec_axes.add_widget(self.slider_ang)
        lay.addWidget(sec_axes)

        sec_rest = CollapsibleSection("RESTRIÇÕES DE PINTURA", content)
        self.chk_stop = QtWidgets.QCheckBox("Parar traço no centro (Stop-at-Center)")
        self.chk_stop.setChecked(self.state.get("stop_at_center", False))
        self.chk_stop.toggled.connect(self._on_changed)
        sec_rest.add_widget(self.chk_stop)

        self.chk_lock = QtWidgets.QCheckBox("Bloquear posição do centro no canvas")
        self.chk_lock.setChecked(self.state.get("locked", False))
        self.chk_lock.toggled.connect(self._on_changed)
        sec_rest.add_widget(self.chk_lock)
        lay.addWidget(sec_rest)
        lay.addStretch()

        scroll.setWidget(content)
        return scroll

    def _on_tab(self, idx):
        self.stack.setCurrentIndex(idx)

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

        self.state["segments"] = int(self.slider_seg.value())
        self.state["angle"] = float(self.slider_ang.value())
        self.state["stop_at_center"] = self.chk_stop.isChecked()
        self.state["locked"] = self.chk_lock.isChecked()

        # If user is interacting with Curvilinear 6P tab and no ruler is active, auto-activate 6P
        if self.stack.currentIndex() == 0 and self.state.get("ruler_type") == "none":
            self.state["ruler_type"] = "curvilinear"
            self.state["ruler_idx"] = 6

        # If user is interacting with Symmetry tab and no symmetry is active, auto-activate radial
        if self.stack.currentIndex() == 2 and self.state.get("sym_type") == "none":
            self.state["sym_type"] = "radial"
            self.state["sym_idx"] = 4

        self.settingsChanged.emit(self.state)

    def sync_from_state(self, state: dict):
        self.state.update(state)
        all_widgets = [
            self.slider_yaw, self.slider_pitch, self.slider_fov, self.slider_sens, self.slider_seg, self.slider_ang,
            self.combo_density, self.combo_aspect, self.combo_snap_mode,
            self.chk_ring, self.chk_straight_v, self.chk_v, self.chk_vps, self.chk_h, self.chk_letterbox,
            self.chk_d, self.chk_cube, self.chk_ground, self.chk_ceiling, self.chk_ground_v, self.chk_ceiling_v,
            self.chk_dynamic, self.chk_hint, self.chk_hide, self.chk_stop, self.chk_lock
        ]
        for w in all_widgets: w.blockSignals(True)
        try:
            self.slider_yaw.setValue(int(self.state.get("yaw", 0)))
            self.slider_pitch.setValue(int(self.state.get("pitch", 0)))
            self.slider_fov.setValue(int(self.state.get("fov", 130)))
            self.combo_density.setCurrentIndex(self.state.get("density_idx", 1))
            self.chk_ring.setChecked(self.state.get("show_ring", True))
            self.chk_straight_v.setChecked(self.state.get("show_straight_verticals", False))
            self.chk_v.setChecked(self.state.get("show_v", True))
            self.chk_vps.setChecked(self.state.get("show_vps", False))
            self.chk_h.setChecked(self.state.get("show_h", True))
            self.chk_letterbox.setChecked(self.state.get("show_letterbox", False))
            self.chk_d.setChecked(self.state.get("show_d", True))
            self.chk_cube.setChecked(self.state.get("show_cube", False))
            self.chk_ground.setChecked(self.state.get("show_ground", False))
            self.chk_ceiling.setChecked(self.state.get("show_ceiling", False))
            self.chk_ground_v.setChecked(self.state.get("show_ground_verticals", False))
            self.chk_ceiling_v.setChecked(self.state.get("show_ceiling_verticals", False))
            self.combo_aspect.setCurrentText(self.state.get("aspect_ratio", "16:9"))
            mode_map = {"auto": 0, "v": 1, "h": 2, "d": 3}
            self.combo_snap_mode.setCurrentIndex(mode_map.get(self.state.get("snap_mode", "auto"), 0))
            self.slider_sens.setValue(int(self.state.get("snap_sensitivity", 3)))
            self.chk_dynamic.setChecked(self.state.get("snap_dynamic", True))
            self.chk_hint.setChecked(self.state.get("show_hint", True))
            self.chk_hide.setChecked(self.state.get("hidden", False))
            self.slider_seg.setValue(int(self.state.get("segments", 6)))
            self.slider_ang.setValue(int(self.state.get("angle", 0)))
            self.chk_stop.setChecked(self.state.get("stop_at_center", False))
            self.chk_lock.setChecked(self.state.get("locked", False))
        finally:
            for w in all_widgets: w.blockSignals(False)

    def _on_reset(self):
        self.sync_from_state({
            "yaw": 0.0, "pitch": 0.0, "fov": 130.0, "density_idx": 1, "density": 30.0,
            "show_ring": True, "show_straight_verticals": False, "show_v": True, "show_vps": False,
            "show_h": True, "show_letterbox": False, "show_d": True, "show_cube": False,
            "show_ground": False, "show_ceiling": False, "show_ground_verticals": False,
            "show_ceiling_verticals": False, "aspect_ratio": "16:9", "snap_mode": "auto",
            "snap_sensitivity": 3.0, "snap_dynamic": True, "show_hint": True, "hidden": False,
            "segments": 6, "angle": 0.0, "stop_at_center": False, "locked": False
        })
        self._on_changed()

    def _apply_theme(self, _=""):
        from ui.core.icons import get_icon
        from ui.core.theme.manager import ThemeManager

        text = ThemeManager.instance().get_color("text_main")
        self.btn_close.setIcon(get_icon("close", text))


