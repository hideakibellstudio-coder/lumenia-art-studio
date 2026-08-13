"""
AdvancedPanel — Configurações Avançadas do Pincel & Dinâmica por Motor ALADYN
================================================================================
Janela flutuante contendo:
- Tab "Pincel": Geometria da Ponta (BrushTip), Textura do Pincel e Parâmetros Base.
- Tab "Dinâmica por Motor": Parâmetros exclusivos do mini-motor nativo ativo (Lápis, Nanquim, Marcador, Blur, Smudge, Aquarela, Óleo Impasto).
"""

import math
from PySide6 import QtWidgets, QtCore, QtGui
from .collapsible_section import CollapsibleSection


class NonScrollComboBox(QtWidgets.QComboBox):
    """Subclasse de QComboBox que ignora a roda do mouse para permitir rolagem suave do painel."""
    def wheelEvent(self, event):
        event.ignore()


class DynamicEngineParamsWidget(QtWidgets.QWidget):
    """Container dinâmico que exibe os sliders exclusivos de cada mini-motor C++."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)
        self._current_engine_type = 0
        self._build_empty()

    def _build_empty(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def set_engine_type(self, engine_type: int):
        self._current_engine_type = engine_type
        self._build_empty()

        from ui.core.widgets.slider import LabeledSlider
        from ui.core.engine.registry import EngineRegistry

        backend = EngineRegistry.instance().get_backend()

        if engine_type == 1:  # Pencil
            lbl = QtWidgets.QLabel("🖍️ Parâmetros de Lápis & Carvão")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_hard = LabeledSlider("Dureza do Grafite (2H-6B):", 1, 100, 50, "%")
            sl_hard.valueChanged.connect(lambda v: self._set_pencil_hard(backend, v / 100.0))
            self.layout.addWidget(sl_hard)

            chk_tilt = QtWidgets.QCheckBox("Sombra por Inclinação (Tilt Shading)")
            chk_tilt.stateChanged.connect(lambda s: self._set_pencil_tilt(backend, chk_tilt.isChecked()))
            self.layout.addWidget(chk_tilt)

        elif engine_type == 2:  # Inker
            lbl = QtWidgets.QLabel("🖊️ Parâmetros de Caneta & Nanquim")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_flow = LabeledSlider("Taxa de Vazão (Ink Flow):", 1, 100, 100, "%")
            sl_flow.valueChanged.connect(lambda v: self._set_inker_flow(backend, v / 100.0))
            self.layout.addWidget(sl_flow)

            sl_taper = LabeledSlider("Suavização (Taper Smoothing):", 0, 100, 70, "%")
            sl_taper.valueChanged.connect(lambda v: self._set_inker_taper(backend, v / 100.0))
            self.layout.addWidget(sl_taper)

        elif engine_type == 4:  # Marker
            lbl = QtWidgets.QLabel("🖊️ Parâmetros de Marcador & Feltro")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_wet = LabeledSlider("Umidade do Solvente:", 0, 100, 60, "%")
            sl_wet.valueChanged.connect(lambda v: self._set_marker_wet(backend, v / 100.0))
            self.layout.addWidget(sl_wet)

            sl_edge = LabeledSlider("Escurecimento de Borda:", 0, 100, 40, "%")
            sl_edge.valueChanged.connect(lambda v: self._set_marker_edge(backend, v / 100.0))
            self.layout.addWidget(sl_edge)

        elif engine_type == 5:  # Blur
            lbl = QtWidgets.QLabel("🌀 Parâmetros de Blur / Desfoque")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_rad = LabeledSlider("Raio do Desfoque:", 1, 10, 2, "px")
            sl_rad.valueChanged.connect(lambda v: self._set_blur_radius(backend, int(v)))
            self.layout.addWidget(sl_rad)

            sl_str = LabeledSlider("Força do Blur:", 1, 100, 60, "%")
            sl_str.valueChanged.connect(lambda v: self._set_blur_strength(backend, v / 100.0))
            self.layout.addWidget(sl_str)

        elif engine_type == 6:  # Smudge
            lbl = QtWidgets.QLabel("🌊 Parâmetros de Smudge / Arrasto")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_pick = LabeledSlider("Coleta de Cor (Pickup):", 0, 100, 70, "%")
            sl_pick.valueChanged.connect(lambda v: self._set_smudge_pick(backend, v / 100.0))
            self.layout.addWidget(sl_pick)

            sl_mix = LabeledSlider("Razão de Mistura (Mix):", 0, 100, 50, "%")
            sl_mix.valueChanged.connect(lambda v: self._set_smudge_mix(backend, v / 100.0))
            self.layout.addWidget(sl_mix)

            sl_str = LabeledSlider("Arrasto da Cor (Stretch):", 0, 100, 80, "%")
            sl_str.valueChanged.connect(lambda v: self._set_smudge_stretch(backend, v / 100.0))
            self.layout.addWidget(sl_str)

        elif engine_type == 7:  # Watercolor
            lbl = QtWidgets.QLabel("🎨 Parâmetros de Aquarela Realista")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_water = LabeledSlider("Nível de Água (Water Level):", 0, 100, 80, "%")
            sl_water.valueChanged.connect(lambda v: self._set_wc_water(backend, v / 100.0))
            self.layout.addWidget(sl_water)

            sl_bleed = LabeledSlider("Sangria de Pigmento (Bleed):", 0, 100, 80, "%")
            sl_bleed.valueChanged.connect(lambda v: self._set_wc_bleed(backend, v / 100.0))
            self.layout.addWidget(sl_bleed)

            sl_fringe = LabeledSlider("Borda de Secagem (Fringe):", 0, 100, 30, "%")
            sl_fringe.valueChanged.connect(lambda v: self._set_wc_fringe(backend, v / 100.0))
            self.layout.addWidget(sl_fringe)

            sl_gran = LabeledSlider("Granulação do Papel:", 0, 100, 40, "%")
            sl_gran.valueChanged.connect(lambda v: self._set_wc_gran(backend, v / 100.0))
            self.layout.addWidget(sl_gran)

        elif engine_type == 8:  # OilImpasto
            lbl = QtWidgets.QLabel("🛢️ Parâmetros de Óleo 3D & Impasto")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_depth = LabeledSlider("Profundidade 3D (Impasto):", 0, 100, 90, "%")
            sl_depth.valueChanged.connect(lambda v: self._set_oil_depth(backend, v / 100.0))
            self.layout.addWidget(sl_depth)

            sl_groove = LabeledSlider("Sulcos de Cerdas:", 0, 100, 80, "%")
            sl_groove.valueChanged.connect(lambda v: self._set_oil_grooves(backend, v / 100.0))
            self.layout.addWidget(sl_groove)

            sl_visc = LabeledSlider("Viscosidade da Tinta:", 0, 100, 80, "%")
            sl_visc.valueChanged.connect(lambda v: self._set_oil_visc(backend, v / 100.0))
            self.layout.addWidget(sl_visc)

            sl_spec = LabeledSlider("Brilho Especular:", 0, 100, 70, "%")
            sl_spec.valueChanged.connect(lambda v: self._set_oil_spec(backend, v / 100.0))
            self.layout.addWidget(sl_spec)

        else:
            lbl = QtWidgets.QLabel("💨 Parâmetros de Borrifo / Spray (Pincel Básico)")
            lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
            self.layout.addWidget(lbl)

            sl_scat = LabeledSlider("Contagem de Borrifos / Spray:", 1, 10, 1, "dabs")
            if backend and hasattr(backend, "_facade") and backend._facade:
                sl_scat.setValue(int(backend._facade.get_brush_profile().scatter_count))
            sl_scat.valueChanged.connect(lambda v: self._set_scatter_count(backend, int(v)))
            self.layout.addWidget(sl_scat)

        self.layout.addStretch()

    def _set_scatter_count(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().scatter_count = int(v)

    # Helpers FFI protegidos para atualizar structs nativas C++
    def _set_pencil_hard(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().pencil_params.graphite_hardness = float(v)

    def _set_pencil_tilt(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().pencil_params.tilt_shading_enabled = bool(v)

    def _set_inker_flow(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().inker_params.ink_flow_rate = float(v)

    def _set_inker_taper(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().inker_params.taper_smoothing = float(v)

    def _set_marker_wet(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().marker_params.solvent_wetness = float(v)

    def _set_marker_edge(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().marker_params.edge_darkening = float(v)

    def _set_blur_radius(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().blur_params.blur_radius = int(v)

    def _set_blur_strength(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().blur_params.blur_strength = float(v)

    def _set_smudge_pick(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().smudge_params.color_pickup = float(v)

    def _set_smudge_mix(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().smudge_params.mix_ratio = float(v)

    def _set_smudge_stretch(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().smudge_params.smudge_stretch = float(v)

    def _set_wc_water(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().watercolor_params.water_level = float(v)

    def _set_wc_bleed(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().watercolor_params.pigment_bleed = float(v)

    def _set_wc_fringe(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().watercolor_params.fringe_intensity = float(v)

    def _set_wc_gran(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().watercolor_params.granulation = float(v)

    def _set_oil_depth(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().oil_params.impasto_depth = float(v)

    def _set_oil_grooves(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().oil_params.bristle_grooves = float(v)

    def _set_oil_visc(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().oil_params.viscosity = float(v)

    def _set_oil_spec(self, b, v):
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().oil_params.specular_brilliance = float(v)


class AdvancedPanel(QtWidgets.QDialog):
    # Signals
    pressureChanged           = QtCore.Signal(float)
    pressureCurvePowerChanged = QtCore.Signal(float)
    stabilizerWeightChanged   = QtCore.Signal(float)
    spacingChanged            = QtCore.Signal(float)
    minDensityActiveChanged   = QtCore.Signal(bool)
    minDensityValueChanged    = QtCore.Signal(float)
    contrastChanged           = QtCore.Signal(float)
    invertHeightChanged       = QtCore.Signal(bool)
    loadShapeRequested        = QtCore.Signal()
    loadHeightmapRequested    = QtCore.Signal()
    sizeChanged               = QtCore.Signal(float)
    opacityChanged            = QtCore.Signal(float)
    pinToggled                = QtCore.Signal(str, bool)

    def __init__(self, parent=None):
        flags = QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint
        super().__init__(parent, flags)
        self.setWindowTitle("Configurações Avançadas")
        self.setMinimumWidth(330)
        self.setMinimumHeight(440)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._drag_pos = None
        self._build_ui()

        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme("")

    # ── Drag ──────────────────────────────────────────────────────────
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
        workspace = None
        left_dock = None

        while curr:
            if hasattr(curr, "left_dock") and hasattr(curr, "workspace_area"):
                workspace = curr
                left_dock = curr.left_dock
                break
            curr = curr.parentWidget()

        scr = anchor_widget.screen().availableGeometry()

        if workspace and left_dock:
            dock_right = left_dock.mapToGlobal(QtCore.QPoint(left_dock.width(), 0)).x()
            if hasattr(left_dock, "drawer_container") and left_dock.drawer_container.isVisible():
                drawer_w = left_dock.drawer_container.width()
                drawer_right = left_dock.drawer_container.mapToGlobal(QtCore.QPoint(drawer_w, 0)).x()
                dock_right = max(dock_right, drawer_right)

            workspace_global = workspace.workspace_area.mapToGlobal(QtCore.QPoint(0, 0))
            x = dock_right + 10
            y = workspace_global.y() + 10
            target_h = workspace.workspace_area.height() - 20
        else:
            curr = anchor_widget
            dock_parent = anchor_widget
            while curr and curr.parentWidget():
                curr = curr.parentWidget()
                if curr.width() > 180:
                    dock_parent = curr

            top_left = dock_parent.mapToGlobal(QtCore.QPoint(0, 0))
            dock_right = top_left.x() + dock_parent.width()
            x = dock_right + 10
            y = top_left.y() + 10
            target_h = scr.bottom() - y - 20

        if x + self.width() > scr.right():
            x = max(scr.left() + 10, scr.right() - self.width() - 10)

        target_h = max(420, target_h)
        self.setFixedHeight(target_h)

        if y + target_h > scr.bottom():
            y = max(scr.top() + 10, scr.bottom() - target_h - 10)

        self.move(QtCore.QPoint(x, y))
        self.show()
        self.raise_()
        self.activateWindow()

    # ── UI ────────────────────────────────────────────────────────────
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

        # Tab bar
        self.tab_bar = QtWidgets.QTabBar()
        self.tab_bar.setExpanding(True)
        self.tab_bar.addTab("Pincel")
        self.tab_bar.addTab("Dinâmica por Motor")
        self.tab_bar.setObjectName("AdvTabBar")
        self.tab_bar.currentChanged.connect(self._on_tab)

        tab_wrap = QtWidgets.QWidget()
        tab_wrap.setObjectName("AdvTabWrap")
        tw = QtWidgets.QHBoxLayout(tab_wrap)
        tw.setContentsMargins(8, 6, 8, 0)
        tw.addWidget(self.tab_bar, 1)
        outer.addWidget(tab_wrap)

        self.stack = QtWidgets.QStackedWidget()
        outer.addWidget(self.stack)

        # Page 0: Pincel (Pincel Ponta + Textura + Base)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        scroll_content = QtWidgets.QWidget()
        pb = QtWidgets.QVBoxLayout(scroll_content)
        pb.setContentsMargins(8, 4, 8, 8)
        pb.setSpacing(4)

        self._build_brush_page(pb)
        pb.addStretch()

        scroll.setWidget(scroll_content)
        self.stack.addWidget(scroll)

        # Page 1: Dinâmica por Motor (Substituição da aba anterior)
        scroll_dyn = QtWidgets.QScrollArea()
        scroll_dyn.setWidgetResizable(True)
        scroll_dyn.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_dyn.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        scroll_dyn_content = QtWidgets.QWidget()
        dl = QtWidgets.QVBoxLayout(scroll_dyn_content)
        dl.setContentsMargins(8, 6, 8, 8)

        self.dyn_params_widget = DynamicEngineParamsWidget(scroll_dyn_content)
        dl.addWidget(self.dyn_params_widget)

        scroll_dyn.setWidget(scroll_dyn_content)
        self.stack.addWidget(scroll_dyn)

        self._draw_default_thumbnails()

    def set_active_engine_type(self, engine_type: int):
        if hasattr(self, "dyn_params_widget"):
            self.dyn_params_widget.set_engine_type(engine_type)

    def _make_title_bar(self) -> QtWidgets.QWidget:
        from ui.core.icons import get_icon

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

        title = QtWidgets.QLabel("CONFIGURAÇÕES AVANÇADAS DE PINCEL")
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

    def _build_brush_page(self, layout: QtWidgets.QVBoxLayout):
        from ui.core.widgets.slider import LabeledSlider

        # ── 1. Tamanho, Opacidade & Mesclagem ─────────────────────────
        sec_so = CollapsibleSection("1. Tamanho, Opacidade & Mesclagem", expanded=True)
        so_w = QtWidgets.QWidget()
        so_lo = QtWidgets.QVBoxLayout(so_w)
        so_lo.setContentsMargins(0, 0, 0, 0)
        so_lo.setSpacing(6)

        self.slider_size = LabeledSlider("Tamanho:", 1, 500, 24, "px", param_name="size", show_pin=True, default_pinned=True)
        self.slider_size.valueChanged.connect(self.sizeChanged.emit)
        self.slider_size.valueChanged.connect(self._on_brush_size_changed)
        self.slider_size.pinToggled.connect(self.pinToggled.emit)
        so_lo.addWidget(self.slider_size)

        self.sl_min_size = LabeledSlider("Tamanho Mínimo (Pressão):", 0, 100, 0, "%")
        self.sl_min_size.valueChanged.connect(self._on_min_size)
        so_lo.addWidget(self.sl_min_size)

        self.slider_opacity = LabeledSlider("Opacidade:", 1, 100, 100, "%", param_name="opacity", show_pin=True, default_pinned=True)
        self.slider_opacity.valueChanged.connect(lambda v: self.opacityChanged.emit(v / 100.0))
        self.slider_opacity.valueChanged.connect(self._on_brush_opacity_changed)
        self.slider_opacity.pinToggled.connect(self.pinToggled.emit)
        so_lo.addWidget(self.slider_opacity)

        self.sl_min_op = LabeledSlider("Opacidade Mínima (Pressão):", 0, 100, 0, "%")
        self.sl_min_op.valueChanged.connect(self._on_min_opacity)
        so_lo.addWidget(self.sl_min_op)

        so_lo.addWidget(QtWidgets.QLabel("Modo de Mesclagem (DabBlendMode):"))
        self.cmb_blend = NonScrollComboBox()
        self.cmb_blend.addItems([
            "Normal (Alpha Over)",
            "Multiplicação (Marcador/Feltro)",
            "Aditivo (Luz / Glow)",
            "Borracha (Alpha Erase)"
        ])
        self.cmb_blend.currentIndexChanged.connect(self._on_blend_mode)
        so_lo.addWidget(self.cmb_blend)

        self.chk_vel_size = QtWidgets.QCheckBox("Variação por Velocidade (Velocity Size)")
        self.chk_vel_size.stateChanged.connect(self._on_vel_size)
        so_lo.addWidget(self.chk_vel_size)

        self.slider_stabilizer = LabeledSlider("Suavização (Estabilizador):", 0, 98, 40, "%", param_name="stabilizer", show_pin=True, default_pinned=False)
        self.slider_stabilizer.valueChanged.connect(lambda v: self.stabilizerWeightChanged.emit(v / 100.0))
        self.slider_stabilizer.valueChanged.connect(self._on_stabilizer_changed)
        self.slider_stabilizer.pinToggled.connect(self.pinToggled.emit)
        so_lo.addWidget(self.slider_stabilizer)

        sec_so.add_widget(so_w)
        layout.addWidget(sec_so)

        # ── 2. Geometria da Ponta (BrushTip) ─────────────────────────
        sec_tip = CollapsibleSection("2. Geometria da Ponta", expanded=True)
        tip_w = QtWidgets.QWidget()
        tip_lo = QtWidgets.QVBoxLayout(tip_w)
        tip_lo.setContentsMargins(0, 0, 0, 0)
        tip_lo.setSpacing(6)

        tip_header = QtWidgets.QHBoxLayout()
        self.shape_preview = QtWidgets.QLabel()
        self.shape_preview.setFixedSize(46, 46)
        self.shape_preview.setObjectName("BTexPreview")
        self.shape_preview.setAlignment(QtCore.Qt.AlignCenter)
        tip_header.addWidget(self.shape_preview)

        tip_info = QtWidgets.QWidget()
        tip_info_lo = QtWidgets.QVBoxLayout(tip_info)
        tip_info_lo.setContentsMargins(4, 0, 0, 0)
        tip_info_lo.setSpacing(4)

        self.cmb_shape = NonScrollComboBox()
        self.cmb_shape.addItems(["Ponta Suave (Radial)", "Ponta Dura (Circular)", "Cerdas Secas", "Quadrado / Chato"])
        self.cmb_shape.currentIndexChanged.connect(self._on_shape_preset_changed)

        btn_load_shape = QtWidgets.QPushButton("Carregar PNG da Ponta")
        btn_load_shape.setObjectName("BTexBtn")
        btn_load_shape.setFixedHeight(22)
        btn_load_shape.setCursor(QtCore.Qt.PointingHandCursor)
        btn_load_shape.clicked.connect(self.loadShapeRequested.emit)

        tip_info_lo.addWidget(self.cmb_shape)
        tip_info_lo.addWidget(btn_load_shape)
        tip_header.addWidget(tip_info, 1)
        tip_lo.addLayout(tip_header)

        self.sl_hardness = LabeledSlider("Dureza da Ponta (Hardness):", 0, 100, 100, "%")
        self.sl_hardness.valueChanged.connect(self._on_tip_hardness)
        tip_lo.addWidget(self.sl_hardness)

        self.sl_angle = LabeledSlider("Ângulo da Ponta:", 0, 360, 0, "°")
        self.sl_angle.valueChanged.connect(self._on_tip_angle)
        tip_lo.addWidget(self.sl_angle)

        self.sl_press_angle = LabeledSlider("Ângulo por Pressão:", 0, 360, 0, "°")
        self.sl_press_angle.valueChanged.connect(self._on_press_angle)
        tip_lo.addWidget(self.sl_press_angle)

        self.sl_aspect = LabeledSlider("Elipse / Proporção:", 1, 100, 100, "%")
        self.sl_aspect.valueChanged.connect(self._on_tip_aspect)
        tip_lo.addWidget(self.sl_aspect)

        self.chk_follow = QtWidgets.QCheckBox("Seguir Direção do Traço (Follow Stroke)")
        self.chk_follow.stateChanged.connect(self._on_tip_follow)
        tip_lo.addWidget(self.chk_follow)

        sec_tip.add_widget(tip_w)
        layout.addWidget(sec_tip)

        # ── 3. Jitters (Variações Aleatórias) ─────────────────────────
        sec_jit = CollapsibleSection("3. Jitters (Variações Aleatórias)", expanded=True)
        jit_w = QtWidgets.QWidget()
        jit_lo = QtWidgets.QVBoxLayout(jit_w)
        jit_lo.setContentsMargins(0, 0, 0, 0)
        jit_lo.setSpacing(6)

        self.sl_jit_size = LabeledSlider("Jitter de Tamanho:", 0, 100, 0, "%")
        self.sl_jit_size.valueChanged.connect(self._on_jit_size)
        jit_lo.addWidget(self.sl_jit_size)

        self.sl_jit_angle = LabeledSlider("Jitter de Rotação:", 0, 100, 0, "%")
        self.sl_jit_angle.valueChanged.connect(self._on_jit_angle)
        jit_lo.addWidget(self.sl_jit_angle)

        self.sl_jit_pos = LabeledSlider("Jitter de Posição (Deslocamento):", 0, 100, 0, "%")
        self.sl_jit_pos.valueChanged.connect(self._on_jit_pos)
        jit_lo.addWidget(self.sl_jit_pos)

        sec_jit.add_widget(jit_w)
        layout.addWidget(sec_jit)

        # ── 4. Textura do Pincel ─────────────────────────────────────
        sec_ponta = CollapsibleSection("4. Textura do Pincel (Matéria)", expanded=True)
        ponta_widget = QtWidgets.QWidget()
        ponta_layout = QtWidgets.QVBoxLayout(ponta_widget)
        ponta_layout.setContentsMargins(0, 0, 0, 0)
        ponta_layout.setSpacing(6)

        tex_header = QtWidgets.QHBoxLayout()
        self.preview_b_grain = QtWidgets.QLabel()
        self.preview_b_grain.setFixedSize(46, 46)
        self.preview_b_grain.setObjectName("BTexPreview")
        self.preview_b_grain.setAlignment(QtCore.Qt.AlignCenter)
        tex_header.addWidget(self.preview_b_grain)

        tex_info = QtWidgets.QWidget()
        tex_info_lo = QtWidgets.QVBoxLayout(tex_info)
        tex_info_lo.setContentsMargins(4, 0, 0, 0)
        tex_info_lo.setSpacing(4)

        self.cmb_b_grain = NonScrollComboBox()
        self.cmb_b_grain.addItems(["Grão Fino", "Papel Aquarela", "Tela de Óleo", "Ruído Puro"])
        self.cmb_b_grain.currentIndexChanged.connect(self._on_b_grain_preset_changed)

        btn_load_height = QtWidgets.QPushButton("Carregar PNG da Textura")
        btn_load_height.setObjectName("BTexBtn")
        btn_load_height.setFixedHeight(22)
        btn_load_height.setCursor(QtCore.Qt.PointingHandCursor)
        btn_load_height.clicked.connect(self.loadHeightmapRequested.emit)

        tex_info_lo.addWidget(self.cmb_b_grain)
        tex_info_lo.addWidget(btn_load_height)
        tex_header.addWidget(tex_info, 1)
        ponta_layout.addLayout(tex_header)

        self.chk_b_grain = QtWidgets.QCheckBox("Ativar Textura no Pincel")
        self.chk_b_grain.setChecked(True)
        self.chk_b_grain.stateChanged.connect(self._on_b_grain_enabled)
        ponta_layout.addWidget(self.chk_b_grain)

        self.sl_b_scale = LabeledSlider("Escala da Textura:", 10, 500, 100, "%")
        self.sl_b_scale.valueChanged.connect(self._on_b_grain_scale)
        ponta_layout.addWidget(self.sl_b_scale)

        self.slider_contrast = LabeledSlider("Contraste da Textura (Dureza):", 10, 300, 100, "%", param_name="contrast", show_pin=True, default_pinned=False)
        self.slider_contrast.valueChanged.connect(self.contrastChanged.emit)
        self.slider_contrast.valueChanged.connect(self._on_b_grain_contrast)
        self.slider_contrast.pinToggled.connect(self.pinToggled.emit)
        ponta_layout.addWidget(self.slider_contrast)

        self.chk_invert = QtWidgets.QCheckBox("Inverter Topografia")
        self.chk_invert.stateChanged.connect(
            lambda _: self.invertHeightChanged.emit(self.chk_invert.isChecked())
        )
        ponta_layout.addWidget(self.chk_invert)

        sec_ponta.add_widget(ponta_widget)
        layout.addWidget(sec_ponta)

        # ── 5. Espaçamento do Traço ───────────────────────────────────
        sec_trace = CollapsibleSection("5. Espaçamento do Traço", expanded=True)

        self.slider_spacing = LabeledSlider("Espaçamento entre Dabs:", 1, 100, 10, "%", param_name="spacing", show_pin=True, default_pinned=False)
        self.slider_spacing.valueChanged.connect(lambda v: self.spacingChanged.emit(v / 100.0))
        self.slider_spacing.valueChanged.connect(self._on_spacing_changed)
        self.slider_spacing.pinToggled.connect(self.pinToggled.emit)
        sec_trace.add_widget(self.slider_spacing)

        layout.addWidget(sec_trace)

    def sync_from_engine_profile(self):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if not b or not hasattr(b, "_facade") or not b._facade:
            return

        facade = b._facade
        prof = facade.get_brush_profile()
        engine_type = facade.get_active_engine_type()

        self.set_active_engine_type(engine_type)

        widgets_to_block = [
            getattr(self, "slider_size", None),
            getattr(self, "sl_min_size", None),
            getattr(self, "slider_opacity", None),
            getattr(self, "sl_min_op", None),
            getattr(self, "cmb_blend", None),
            getattr(self, "chk_vel_size", None),
            getattr(self, "slider_stabilizer", None),
            getattr(self, "sl_hardness", None),
            getattr(self, "sl_angle", None),
            getattr(self, "sl_press_angle", None),
            getattr(self, "sl_aspect", None),
            getattr(self, "chk_follow", None),
            getattr(self, "sl_jit_size", None),
            getattr(self, "sl_jit_angle", None),
            getattr(self, "sl_jit_pos", None),
            getattr(self, "chk_b_grain", None),
            getattr(self, "sl_b_scale", None),
            getattr(self, "slider_contrast", None),
            getattr(self, "chk_invert", None),
            getattr(self, "slider_spacing", None),
        ]

        for w in widgets_to_block:
            if w:
                w.blockSignals(True)

        try:
            if hasattr(self, "slider_size"):
                self.slider_size.setValue(int(prof.brush_size))
            if hasattr(self, "sl_min_size"):
                self.sl_min_size.setValue(int(prof.min_size_percent * 100))
            if hasattr(self, "slider_opacity"):
                self.slider_opacity.setValue(int(prof.opacity * 100))
            if hasattr(self, "sl_min_op"):
                self.sl_min_op.setValue(int(prof.min_opacity_percent * 100))
            if hasattr(self, "cmb_blend"):
                bm_val = int(prof.blend_mode.value if hasattr(prof.blend_mode, 'value') else prof.blend_mode)
                self.cmb_blend.setCurrentIndex(min(bm_val, self.cmb_blend.count() - 1))
            if hasattr(self, "chk_vel_size"):
                self.chk_vel_size.setChecked(bool(prof.velocity_size_enabled))
            if hasattr(self, "slider_stabilizer") and hasattr(facade, "get_stabilizer"):
                stab = facade.get_stabilizer()
                if stab:
                    self.slider_stabilizer.setValue(int(stab.get_stabilization_percentage() * 100))
            if hasattr(self, "sl_hardness"):
                self.sl_hardness.setValue(int(prof.hardness * 100))
            if hasattr(self, "sl_angle"):
                self.sl_angle.setValue(int(prof.tip.angle))
            if hasattr(self, "sl_press_angle"):
                self.sl_press_angle.setValue(int(prof.pressure_to_angle))
            if hasattr(self, "sl_aspect"):
                self.sl_aspect.setValue(int(prof.tip.aspect_ratio * 100))
            if hasattr(self, "chk_follow"):
                self.chk_follow.setChecked(bool(prof.tip.follow_stroke))
            if hasattr(self, "sl_jit_size"):
                self.sl_jit_size.setValue(int(prof.tip.jitter_size * 100))
            if hasattr(self, "sl_jit_angle"):
                self.sl_jit_angle.setValue(int(prof.tip.jitter_angle * 100))
            if hasattr(self, "sl_jit_pos"):
                self.sl_jit_pos.setValue(int(prof.tip.jitter_position))
            if hasattr(self, "chk_b_grain"):
                self.chk_b_grain.setChecked(bool(prof.brush_grain_enabled))
            if hasattr(self, "sl_b_scale"):
                self.sl_b_scale.setValue(int(prof.brush_grain_scale * 100))
            if hasattr(self, "slider_contrast"):
                self.slider_contrast.setValue(int(prof.brush_grain_contrast * 100))
            if hasattr(self, "chk_invert"):
                self.chk_invert.setChecked(bool(prof.brush_grain_invert))
            if hasattr(self, "slider_spacing"):
                self.slider_spacing.setValue(int(prof.spacing_factor * 100))
        finally:
            for w in widgets_to_block:
                if w:
                    w.blockSignals(False)

        self.update_shape_preview_from_engine()
        self.update_brush_height_preview_from_engine()

    # Handlers FFI Nativos C++
    def _on_brush_size_changed(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().brush_size = float(v)

    def _on_brush_opacity_changed(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().opacity = float(v / 100.0)

    def _on_min_size(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().min_size_percent = float(v / 100.0)

    def _on_min_opacity(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().min_opacity_percent = float(v / 100.0)

    def _on_blend_mode(self, idx: int):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            if hasattr(b, "_native") and b._native and hasattr(b._native, "DabBlendMode"):
                try:
                    b._facade.get_brush_profile().blend_mode = b._native.DabBlendMode(int(idx))
                except Exception as e:
                    logger.debug(f"Blend mode set error: {e}")

    def _on_vel_size(self, s):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().velocity_size_enabled = bool(self.chk_vel_size.isChecked())

    def _on_stabilizer_changed(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_stabilizer().set_stabilization_percentage(float(v / 100.0))

    def _on_tip_hardness(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().hardness = float(v / 100.0)

    def _on_press_angle(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().pressure_to_angle = float(v)

    def _on_jit_pos(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().tip.jitter_position = float(v)

    def _on_b_grain_contrast(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().brush_grain_contrast = float(v / 100.0)

    def _on_spacing_changed(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().spacing_factor = float(v / 100.0)

    # Handlers da Geometria da Ponta C++
    def update_shape_preview_from_engine(self):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            try:
                buf = b._facade.get_shape_preview_buffer()
                w, h = b._facade.get_shape_preview_dimensions()
                if buf and w > 0 and h > 0:
                    img = QtGui.QImage(bytes(buf), w, h, w, QtGui.QImage.Format_Grayscale8)
                    pix = QtGui.QPixmap.fromImage(img).scaled(46, 46, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    if hasattr(self, "shape_preview"):
                        self.shape_preview.setPixmap(pix)
            except Exception as e:
                logger.debug(f"Shape preview read error: {e}")

    def update_brush_height_preview_from_engine(self):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            try:
                buf = b._facade.get_brush_height_preview_buffer()
                w, h = b._facade.get_brush_height_preview_dimensions()
                if buf and w > 0 and h > 0:
                    img = QtGui.QImage(bytes(buf), w, h, w, QtGui.QImage.Format_Grayscale8)
                    pix = QtGui.QPixmap.fromImage(img).scaled(46, 46, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    if hasattr(self, "preview_b_grain"):
                        self.preview_b_grain.setPixmap(pix)
            except Exception as e:
                logger.debug(f"Brush height preview read error: {e}")

    def _on_shape_preset_changed(self, idx: int):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.set_shape_preset(idx)
            self.update_shape_preview_from_engine()

    def _on_b_grain_preset_changed(self, idx: int):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.set_brush_height_preset(idx)
            self.update_brush_height_preview_from_engine()

    def _on_b_grain_enabled(self, s):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b:
            if hasattr(b, "set_brush_grain_enabled"):
                b.set_brush_grain_enabled(bool(self.chk_b_grain.isChecked()))
            elif hasattr(b, "_facade") and b._facade:
                b._facade.get_brush_profile().brush_grain_enabled = bool(self.chk_b_grain.isChecked())

    def _on_b_grain_scale(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().brush_grain_scale = float(v / 100.0)

    def _on_tip_angle(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().tip.angle = float(v)

    def _on_tip_aspect(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().tip.aspect_ratio = float(v / 100.0)

    def _on_tip_follow(self, s):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().tip.follow_stroke = bool(self.chk_follow.isChecked())

    def _on_jit_size(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().tip.jitter_size = float(v / 100.0)

    def _on_jit_angle(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().tip.jitter_angle = float(v)

    def _on_tab(self, idx):
        self.stack.setCurrentIndex(idx)

    def _draw_default_thumbnails(self):
        # Thumbnail da Ponta
        pm_shape = QtGui.QPixmap(46, 46)
        pm_shape.fill(QtGui.QColor(16, 16, 16))
        p = QtGui.QPainter(pm_shape)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        grad = QtGui.QRadialGradient(23, 23, 23)
        grad.setColorAt(0.0, QtGui.QColor(255, 255, 255, 255))
        grad.setColorAt(0.7, QtGui.QColor(255, 255, 255, 180))
        grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
        p.setBrush(QtGui.QBrush(grad))
        p.setPen(QtCore.Qt.NoPen)
        p.drawRect(0, 0, 46, 46)
        p.end()
        if hasattr(self, "shape_preview"):
            self.shape_preview.setPixmap(pm_shape)

        # Thumbnail da Textura
        pm_grain = QtGui.QPixmap(46, 46)
        pm_grain.fill(QtGui.QColor(24, 24, 32))
        p = QtGui.QPainter(pm_grain)
        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 30), 1))
        for y in range(0, 46, 6):
            for x in range(0, 46, 6):
                if (x + y) % 12 == 0:
                    p.drawRect(x, y, 4, 4)
        p.end()
        if hasattr(self, "preview_b_grain"):
            self.preview_b_grain.setPixmap(pm_grain)

    def _apply_theme(self, _=""):
        from ui.core.theme.manager import ThemeManager
        tm     = ThemeManager.instance()
        bg     = tm.get_color("bg_main")
        bg2    = tm.get_color("bg_panel")
        text   = tm.get_color("text_main")
        muted  = tm.get_color("text_sec")
        accent = tm.get_color("accent")
        border = tm.get_color("border")

        from ui.core.icons import get_icon
        self.btn_close.setIcon(get_icon("close", text))

        self.setStyleSheet(f"""
            AdvancedPanel {{
                background: transparent;
            }}
            #AdvContainer {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            #AdvTitleBar {{
                background: {bg2};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            #AdvTitleLabel {{
                color: {text};
                font-weight: 600;
                font-size: 11px;
            }}
            #AdvTitleIcon {{
                color: {accent};
                font-size: 13px;
            }}
            #AdvCloseBtn {{
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
            #AdvCloseBtn:hover {{
                background: {accent};
            }}
            #AdvSep {{ color: {border}; }}
            #AdvTabWrap {{ background: {bg}; }}
            #AdvTabBar::tab {{
                background: {bg2};
                color: {muted};
                padding: 4px 10px;
                border: 1px solid {border};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 10px;
            }}
            #AdvTabBar::tab:selected {{
                background: {accent};
                color: {text};
                font-weight: 600;
            }}
            #BTexPreview {{
                border: 1px solid {border};
                border-radius: 4px;
                background: {bg};
            }}
            #BTexBtn {{
                background: {bg2};
                color: {text};
                border: 1px solid {border};
                border-radius: 3px;
                font-size: 10px;
                padding: 0 4px;
            }}
            #BTexBtn:hover {{
                border-color: {accent};
                color: {accent};
            }}
            #CollapsHeader {{
                background: {bg2};
                border-radius: 4px;
            }}
            #CollapsHeader:hover {{
                background: {accent};
            }}
            #CollapsArrow {{ color: {muted}; font-size: 10px; }}
            #CollapsTitle {{
                color: {text};
                font-size: 10px;
                font-weight: 600;
            }}
            #CollapsContent {{
                background: transparent;
            }}
            QStackedWidget, QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
                background: transparent;
                background-color: transparent;
            }}
            QStackedWidget {{
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QScrollArea {{
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
                border-bottom-left-radius: 7px;
                border-bottom-right-radius: 7px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: rgba(0, 0, 0, 0.15);
                width: 7px;
                margin: 2px 2px 8px 2px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {muted};
                border-radius: 3px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {accent};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
