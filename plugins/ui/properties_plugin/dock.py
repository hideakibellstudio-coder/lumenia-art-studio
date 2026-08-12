from PySide6 import QtWidgets, QtCore, QtGui
import math
from plugins.ui.brush_plugin.stroke_preview import StrokePreview
from plugins.ui.brush_plugin.compact_slider import CompactSlider
from plugins.ui.brush_plugin.advanced_panel import AdvancedPanel

class BrushDock(QtWidgets.QDockWidget):
    # ── Signals ───────────────────────────────────────────────────────
    colorChanged              = QtCore.Signal(QtGui.QColor)
    sizeChanged               = QtCore.Signal(float)
    opacityChanged            = QtCore.Signal(float)
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
    toolActivated             = QtCore.Signal(str) # "brush" or "eraser"

    def __init__(self, parent=None, initial_color: QtGui.QColor = None):
        super().__init__("Pincel e Cores", parent)
        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QtWidgets.QWidget())
        self.setFixedWidth(280)

        from ui.core.theme.manager import ThemeManager
        theme = ThemeManager.instance()._themes.get(ThemeManager.instance().current_theme, {})
        colors = theme.get("colors", {})
        accent_hex = ThemeManager.instance().resolve_color("ACCENT", colors)
        self._initial_color = initial_color or QtGui.QColor(accent_hex)
        self._adv_panel = None
        self._quick_sliders = []

        self.setup_ui()
        self._draw_default_thumbnails()
        self._init_stroke_preview()

        # Track theme changes
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme("")

    def setup_ui(self):
        # 1. Main container
        dock_contents = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(dock_contents)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 2. Scroll Area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        main_layout.addWidget(scroll)

        # 3. Scroll Content
        scroll_content = QtWidgets.QWidget()
        scroll_content.setObjectName("DockScrollContent")
        layout = QtWidgets.QVBoxLayout(scroll_content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # --- Group 1: Roda de Cores ---
        color_group = QtWidgets.QGroupBox("🎨 Roda de Cores")
        color_group.setObjectName("DockColorGroup")
        color_layout = QtWidgets.QVBoxLayout(color_group)
        color_layout.setContentsMargins(4, 8, 4, 4)

        from plugins.ui.color_plugin.color_wheel import ColorWheelWidget
        self.color_wheel = ColorWheelWidget(self, initial_color=self._initial_color)
        self.color_wheel.colorChanged.connect(self.colorChanged.emit)
        color_layout.addWidget(self.color_wheel)
        layout.addWidget(color_group)

        # Separator line
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setObjectName("DockSep")
        layout.addWidget(sep)

        # --- Group 2: Configurações do Pincel (ToolGrid + Properties) ---
        self.settings_group = QtWidgets.QWidget()
        self.settings_group.setObjectName("DockSettingsGroup")
        settings_layout = QtWidgets.QHBoxLayout(self.settings_group)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(6)

        # Tool Grid Column
        settings_layout.addWidget(self._make_tool_column())

        # Vertical Divider
        vline = QtWidgets.QFrame()
        vline.setFrameShape(QtWidgets.QFrame.VLine)
        vline.setObjectName("DockVLine")
        settings_layout.addWidget(vline)

        # Properties Column
        props = QtWidgets.QWidget()
        props_lo = QtWidgets.QVBoxLayout(props)
        props_lo.setContentsMargins(0, 0, 0, 0)
        props_lo.setSpacing(8)
        self._build_props(props_lo)
        settings_layout.addWidget(props, 1)

        layout.addWidget(self.settings_group)
        layout.addStretch()

        scroll.setWidget(scroll_content)
        self.setWidget(dock_contents)

    # ── Tool Grid column ──────────────────────────────────────────────
    def _make_tool_column(self) -> QtWidgets.QWidget:
        col = QtWidgets.QWidget()
        col.setObjectName("BToolCol")
        col.setFixedWidth(44)
        lo = QtWidgets.QVBoxLayout(col)
        lo.setContentsMargins(4, 4, 4, 4)
        lo.setSpacing(4)
        lo.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

        tools = [
            ("brush",  "🖌", "Pincel",   get_icon("brush")),
            ("eraser", "⬜", "Borracha", get_icon("eraser")),
        ]
        self._tool_buttons = {}
        for tid, emoji, tooltip, icon in tools:
            btn = QtWidgets.QToolButton()
            btn.setFixedSize(32, 32)
            btn.setIconSize(QtCore.QSize(18, 18))
            btn.setCheckable(True)
            btn.setAutoRaise(True)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            if icon and not icon.isNull():
                btn.setIcon(icon)
            else:
                btn.setText(emoji)
            btn.clicked.connect(lambda _, t=tid: self._on_tool(t))
            lo.addWidget(btn)
            self._tool_buttons[tid] = btn

        # Select brush by default
        self._tool_buttons["brush"].setChecked(True)
        lo.addStretch()
        return col

    def _on_tool(self, tool_id: str):
        for tid, btn in self._tool_buttons.items():
            btn.setChecked(tid == tool_id)
        self.toolActivated.emit(tool_id)

    # ── Properties column ─────────────────────────────────────────────
    def _build_props(self, lo: QtWidgets.QVBoxLayout):
        # Row 1: Preset label + Advanced btn
        row1 = QtWidgets.QHBoxLayout()

        self.preset_label = QtWidgets.QLabel("Pincel Padrão")
        self.preset_label.setObjectName("BPresetLabel")

        self.btn_advanced = QtWidgets.QToolButton()
        self.btn_advanced.setFixedSize(28, 28)
        self.btn_advanced.setText("⚙")
        self.btn_advanced.setObjectName("BAdvBtn")
        self.btn_advanced.setToolTip("Configurações Avançadas")
        self.btn_advanced.clicked.connect(self._toggle_advanced)

        row1.addWidget(self.preset_label, 1)
        row1.addWidget(self.btn_advanced)
        lo.addLayout(row1)

        # StrokePreview
        self.stroke_preview = StrokePreview()
        self.stroke_preview.setObjectName("BStrokePreview")
        lo.addWidget(self.stroke_preview)

        # Separator label
        sep_lbl = QtWidgets.QLabel("Parâmetros Rápidos")
        sep_lbl.setObjectName("BSectionLabel")
        lo.addWidget(sep_lbl)

        # Quick sliders (compact)
        self._quick_sliders = []
        self._build_quick_sliders(lo)

        lo.addStretch()

    def _build_texture_row(self) -> QtWidgets.QWidget:
        wrap = QtWidgets.QWidget()
        row  = QtWidgets.QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.setAlignment(QtCore.Qt.AlignHCenter)

        # Shape
        sc = QtWidgets.QVBoxLayout()
        sc.setSpacing(3)
        sc.setAlignment(QtCore.Qt.AlignHCenter)
        lbl_s = QtWidgets.QLabel("Ponta")
        lbl_s.setAlignment(QtCore.Qt.AlignCenter)
        lbl_s.setObjectName("BTexLabel")
        self.shape_preview = QtWidgets.QLabel()
        self.shape_preview.setFixedSize(48, 48)
        self.shape_preview.setObjectName("BTexPreview")
        self.shape_preview.setAlignment(QtCore.Qt.AlignCenter)
        btn_s = QtWidgets.QPushButton("Carregar")
        btn_s.setObjectName("BTexBtn")
        btn_s.setFixedHeight(20)
        btn_s.clicked.connect(self.loadShapeRequested.emit)
        sc.addWidget(lbl_s)
        sc.addWidget(self.shape_preview)
        sc.addWidget(btn_s)
        row.addLayout(sc)

        # Heightmap
        hc = QtWidgets.QVBoxLayout()
        hc.setSpacing(3)
        hc.setAlignment(QtCore.Qt.AlignHCenter)
        lbl_h = QtWidgets.QLabel("Relevo")
        lbl_h.setAlignment(QtCore.Qt.AlignCenter)
        lbl_h.setObjectName("BTexLabel")
        self.heightmap_preview = QtWidgets.QLabel()
        self.heightmap_preview.setFixedSize(48, 48)
        self.heightmap_preview.setObjectName("BTexPreview")
        self.heightmap_preview.setAlignment(QtCore.Qt.AlignCenter)
        btn_h = QtWidgets.QPushButton("Carregar")
        btn_h.setObjectName("BTexBtn")
        btn_h.setFixedHeight(20)
        btn_h.clicked.connect(self.loadHeightmapRequested.emit)
        hc.addWidget(lbl_h)
        hc.addWidget(self.heightmap_preview)
        hc.addWidget(btn_h)
        row.addLayout(hc)

        return wrap

    def _build_quick_sliders(self, lo: QtWidgets.QVBoxLayout):
        def add(prefix, min_v, max_v, default, unit, callback):
            sl = CompactSlider(prefix, min_v, max_v, unit)
            sl.setValue(default)
            sl.valueChanged.connect(callback)
            lo.addWidget(sl)
            self._quick_sliders.append(sl)
            return sl

        self.qs_size = add("Tam: ",  10, 200, 60,  "px",
                           lambda v: self.sizeChanged.emit(float(v)))
        self.qs_opacity = add("Opac: ", 1, 100, 100, "%",
                              lambda v: self.opacityChanged.emit(v / 100.0))

    # ── Advanced panel ────────────────────────────────────────────────
    def _ensure_advanced(self):
        if self._adv_panel is None:
            self._adv_panel = AdvancedPanel(self)
            # Wire signals
            self._adv_panel.pressureChanged.connect(self.pressureChanged.emit)
            self._adv_panel.pressureCurvePowerChanged.connect(self.pressureCurvePowerChanged.emit)
            self._adv_panel.stabilizerWeightChanged.connect(self.stabilizerWeightChanged.emit)
            self._adv_panel.spacingChanged.connect(self.spacingChanged.emit)
            self._adv_panel.minDensityActiveChanged.connect(self.minDensityActiveChanged.emit)
            self._adv_panel.minDensityValueChanged.connect(self.minDensityValueChanged.emit)
            self._adv_panel.contrastChanged.connect(self.contrastChanged.emit)
            self._adv_panel.invertHeightChanged.connect(self.invertHeightChanged.emit)
            self._adv_panel.loadShapeRequested.connect(self.loadShapeRequested.emit)
            self._adv_panel.loadHeightmapRequested.connect(self.loadHeightmapRequested.emit)
            self._adv_panel.sizeChanged.connect(self.sizeChanged.emit)
            self._adv_panel.opacityChanged.connect(self.opacityChanged.emit)

    def _toggle_advanced(self):
        self._ensure_advanced()
        if self._adv_panel.isVisible():
            self._adv_panel.hide()
        else:
            self._adv_panel.show_near(self.settings_group)

    # ── Public API ────────────────────────────────────────────────────
    def update_thumbnail(self, is_shape: bool, file_path: str):
        self._ensure_advanced()
        self._adv_panel.update_thumbnail(is_shape, file_path)

    # Slider value getters
    @property
    def slider_size(self):       return self.qs_size
    @property
    def slider_opacity(self):    return self.qs_opacity

    def _adv(self, attr):
        if self._adv_panel:
            return getattr(self._adv_panel, attr, None)
        return None

    @property
    def slider_pressure(self):
        self._ensure_advanced()
        return self._adv_panel.slider_pressure
    @property
    def slider_curve(self):
        self._ensure_advanced()
        return self._adv_panel.slider_curve
    @property
    def slider_stabilizer(self):
        self._ensure_advanced()
        return self._adv_panel.slider_stabilizer
    @property
    def slider_spacing(self):
        self._ensure_advanced()
        return self._adv_panel.slider_spacing
    @property
    def chk_min_density(self):
        self._ensure_advanced()
        return self._adv_panel.chk_min_density
    @property
    def slider_min_density(self):
        self._ensure_advanced()
        return self._adv_panel.slider_min_density
    @property
    def slider_contrast(self):
        self._ensure_advanced()
        return self._adv_panel.slider_contrast
    @property
    def chk_invert(self):
        self._ensure_advanced()
        return self._adv_panel.chk_invert

    def set_tool_active(self, tool_id: str):
        if tool_id in self._tool_buttons:
            for tid, btn in self._tool_buttons.items():
                btn.setChecked(tid == tool_id)

    # ── Default thumbnails ────────────────────────────────────────────
    def _draw_default_thumbnails(self):
        self._ensure_advanced()
        self._adv_panel._draw_default_thumbnails()

    def _init_stroke_preview(self):
        self.stroke_preview.update_brush_state(
            size=60.0, opacity=1.0, hardness=1.0, color=[0.0, 0.0, 0.0]
        )

    # ── Theme ─────────────────────────────────────────────────────────
    def _apply_theme(self, _=""):
        from ui.core.theme.manager import ThemeManager
        tm     = ThemeManager.instance()
        bg     = tm.get_color("bg_main")
        bg2    = tm.get_color("bg_panel")
        bg3    = tm.get_color("bg_panel")
        text   = tm.get_color("text_main")
        muted  = tm.get_color("text_sec")
        accent = tm.get_color("accent")
        border = tm.get_color("border")

        # Update compact sliders with accent color
        for sl in self._quick_sliders:
            sl.apply_theme(bg3, border, accent, text)

        self.setStyleSheet(f"""
            #DockScrollContent {{
                background: transparent;
            }}
            #DockColorGroup {{
                color: {text};
                font-weight: bold;
                border: 1px solid {border};
                border-radius: 6px;
                margin-top: 4px;
            }}
            #DockSep {{
                color: {border};
                height: 1px;
            }}
            #BToolCol {{
                background: {bg2};
                border-radius: 6px;
                border: 1px solid {border};
            }}
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
            }}
            QToolButton:hover {{
                background: {bg};
                border-color: {border};
            }}
            QToolButton:checked {{
                background: {accent};
                border-color: {accent};
            }}
            #DockVLine {{
                color: {border};
            }}
            #BPresetLabel {{
                color: {text};
                font-size: 11px;
                font-weight: 600;
                background: {bg2};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            #BAdvBtn {{
                background: {bg2};
                border: 1px solid {border};
                border-radius: 4px;
                font-size: 13px;
                color: {text};
            }}
            #BAdvBtn:hover {{
                background: {accent};
                border-color: {accent};
            }}
            #BStrokePreview {{
                border: 1px solid {border};
                border-radius: 6px;
            }}
            #BTexLabel {{
                color: {muted};
                font-size: 10px;
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
            #BSectionLabel {{
                color: {muted};
                font-size: 9px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
        """)


class PropertiesDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Navegador e Camadas", parent)
        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QtWidgets.QWidget())
        self.setFixedWidth(280)


        self.setup_ui()

    def setup_ui(self):
        dock_contents = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(dock_contents)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # --- Navigator ---
        nav_group = QtWidgets.QGroupBox("🧭 Navegador")
        nav_layout = QtWidgets.QVBoxLayout(nav_group)
        nav_layout.setContentsMargins(4, 8, 4, 4)

        from plugins.ui.navigator_plugin.panel import NavigatorPanel

        self.navigator = NavigatorPanel(self)
        nav_layout.addWidget(self.navigator)
        layout.addWidget(nav_group)

        # --- Layers ---
        layers_group = QtWidgets.QGroupBox("🥞 Camadas")
        layers_layout = QtWidgets.QVBoxLayout(layers_group)
        layers_layout.setContentsMargins(0, 4, 0, 0)
        
        from plugins.ui.layers_plugin.panel import LayersPanel

        self.layers = LayersPanel(self)
        layers_layout.addWidget(self.layers)

        layout.addWidget(layers_group, 1)

        self.setWidget(dock_contents)
