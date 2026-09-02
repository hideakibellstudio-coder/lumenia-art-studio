"""
BrushSettingsDialog
────────────────────
Painel flutuante completo do pincel, baseado em BrushC.
Estrutura:
  ┌─ Title bar (drag + Fechar) ─────────────────────────────────┐
  │ [ToolGrid│ Preset combo        [⚙ Avançado]                │
  │          │ ─── StrokePreview ──────────────────────────────│
  │          │ [Ponta 54×54]  [Relevo 54×54]                   │
  │          │ [Carregar →]   [Carregar →]                     │
  │          │ Tam: ████████████████████ 60px                  │
  │          │ Opac:████████████████████ 100%                  │
  └─────────────────────────────────────────────────────────────┘
"""
import os
import math
from PySide6 import QtWidgets, QtCore, QtGui

from ui.core.icons import get_icon

from .stroke_preview   import StrokePreview
from .compact_slider   import CompactSlider
from .advanced_panel   import AdvancedPanel


class BrushSettingsDialog(QtWidgets.QDialog):
    # ── Signals ───────────────────────────────────────────────────────
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

    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setWindowTitle("Pincel")
        self.setFixedWidth(340)

        self._drag_pos    = None
        self._adv_panel   = None   # lazy-created

        self._build_ui()
        self._draw_default_thumbnails()
        self._init_stroke_preview()

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

    # ── Open/close near anchor widget ─────────────────────────────────
    def toggle(self, anchor_widget: QtWidgets.QWidget = None):
        if self.isVisible():
            self.hide()
            if self._adv_panel and self._adv_panel.isVisible():
                self._adv_panel.hide()
            return
        if anchor_widget:
            pos = anchor_widget.mapToGlobal(QtCore.QPoint(0, anchor_widget.height() + 4))
            scr = anchor_widget.screen().availableGeometry()
            if pos.x() + self.width() > scr.right():
                pos.setX(scr.right() - self.width() - 8)
            if pos.y() + self.height() > scr.bottom():
                pos.setY(pos.y() - anchor_widget.height() - self.height() - 8)
            self.move(pos)
        self.show()
        self.raise_()
        self.activateWindow()

    # ── Build UI ──────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._make_title_bar())

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setObjectName("BSep")
        outer.addWidget(sep)

        # ── Body: ToolGrid | Properties ───────────────────────────────
        body = QtWidgets.QWidget()
        body.setObjectName("BBody")
        body_lo = QtWidgets.QHBoxLayout(body)
        body_lo.setContentsMargins(0, 0, 0, 0)
        body_lo.setSpacing(0)
        outer.addWidget(body)

        # Left: Tool column
        body_lo.addWidget(self._make_tool_column())

        # Divider
        vline = QtWidgets.QFrame()
        vline.setFrameShape(QtWidgets.QFrame.VLine)
        vline.setObjectName("BDivider")
        body_lo.addWidget(vline)

        # Right: properties
        props = QtWidgets.QWidget()
        props.setObjectName("BProps")
        props_lo = QtWidgets.QVBoxLayout(props)
        props_lo.setContentsMargins(10, 10, 10, 10)
        props_lo.setSpacing(8)
        self._build_props(props_lo)
        body_lo.addWidget(props, 1)

    def _make_title_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setObjectName("BTitleBar")
        bar.setFixedHeight(34)
        lo = QtWidgets.QHBoxLayout(bar)
        lo.setContentsMargins(10, 0, 8, 0)

        from ui.core.icons import get_icon

        icon = QtWidgets.QLabel()
        icon.setFixedSize(16, 16)
        icon.setPixmap(get_icon("brush").pixmap(16, 16))
        icon.setObjectName("BTitleIcon")
        title = QtWidgets.QLabel("Pincel")
        title.setObjectName("BTitleLabel")

        btn = QtWidgets.QPushButton("Fechar")
        btn.setObjectName("BCloseBtn")
        btn.setFixedHeight(22)
        btn.clicked.connect(self._on_close)

        lo.addWidget(icon)
        lo.addWidget(title)
        lo.addStretch()
        lo.addWidget(btn)
        return bar

    def _on_close(self):
        self.hide()
        if self._adv_panel and self._adv_panel.isVisible():
            self._adv_panel.hide()

    # ── Tool Grid column ──────────────────────────────────────────────
    def _make_tool_column(self) -> QtWidgets.QWidget:
        col = QtWidgets.QWidget()
        col.setObjectName("BToolCol")
        col.setFixedWidth(44)
        lo = QtWidgets.QVBoxLayout(col)
        lo.setContentsMargins(4, 10, 4, 10)
        lo.setSpacing(4)
        lo.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

        from ui.core.icons import get_icon

        tools = [
            ("brush",  "Pincel",   get_icon("brush")),
            ("eraser", "Borracha", get_icon("eraser")),
        ]
        self._tool_buttons = {}
        for tid, tooltip, icon in tools:
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

    # ── Properties column ─────────────────────────────────────────────
    def _build_props(self, lo: QtWidgets.QVBoxLayout):
        # Row 1: Preset label + Advanced btn
        row1 = QtWidgets.QHBoxLayout()

        self.preset_label = QtWidgets.QLabel("Pincel Padrão")
        self.preset_label.setObjectName("BPresetLabel")

        self.btn_advanced = QtWidgets.QToolButton()
        self.btn_advanced.setFixedSize(28, 28)
        self.btn_advanced.setIcon(get_icon("settings"))
        self.btn_advanced.setIconSize(QtCore.QSize(16, 16))
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

        # Texture previews (Ponta + Relevo side by side)
        lo.addWidget(self._build_texture_row())

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
        row.setSpacing(16)
        row.setAlignment(QtCore.Qt.AlignHCenter)

        # Shape
        sc = QtWidgets.QVBoxLayout()
        sc.setSpacing(3)
        sc.setAlignment(QtCore.Qt.AlignHCenter)
        lbl_s = QtWidgets.QLabel("Ponta")
        lbl_s.setAlignment(QtCore.Qt.AlignCenter)
        lbl_s.setObjectName("BTexLabel")
        self.shape_preview = QtWidgets.QLabel()
        self.shape_preview.setFixedSize(54, 54)
        self.shape_preview.setObjectName("BTexPreview")
        self.shape_preview.setAlignment(QtCore.Qt.AlignCenter)
        btn_s = QtWidgets.QPushButton("Carregar")
        btn_s.setObjectName("BTexBtn")
        btn_s.setFixedHeight(22)
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
        self.heightmap_preview.setFixedSize(54, 54)
        self.heightmap_preview.setObjectName("BTexPreview")
        self.heightmap_preview.setAlignment(QtCore.Qt.AlignCenter)
        btn_h = QtWidgets.QPushButton("Carregar")
        btn_h.setObjectName("BTexBtn")
        btn_h.setFixedHeight(22)
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

    def _toggle_advanced(self):
        self._ensure_advanced()
        if self._adv_panel.isVisible():
            self._adv_panel.hide()
        else:
            self._adv_panel.show_near(self)

    # ── Public API ────────────────────────────────────────────────────
    def update_thumbnail(self, is_shape: bool, file_path: str):
        pixmap = QtGui.QPixmap(file_path)
        if not pixmap.isNull():
            label = self.shape_preview if is_shape else self.heightmap_preview
            label.setPixmap(
                pixmap.scaled(54, 54, QtCore.Qt.KeepAspectRatio,
                              QtCore.Qt.SmoothTransformation)
            )

    # Slider value getters for _sync_all_properties in app.py
    @property
    def slider_size(self):       return self.qs_size
    @property
    def slider_opacity(self):    return self.qs_opacity

    def _adv(self, attr):
        """Safe access to advanced panel slider (returns None if not created)."""
        if self._adv_panel:
            return getattr(self._adv_panel, attr, None)
        return None

    def __getattr__(self, name: str):
        if name.startswith(("slider_", "chk_")):
            self._ensure_advanced()
            return getattr(self._adv_panel, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # ── Default thumbnails ────────────────────────────────────────────
    def _draw_default_thumbnails(self):
        pm = QtGui.QPixmap(54, 54)
        pm.fill(QtGui.QColor(16, 16, 16))
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        grad = QtGui.QRadialGradient(27, 27, 27)
        grad.setColorAt(0.0, QtGui.QColor(255, 255, 255, 255))
        grad.setColorAt(0.8, QtGui.QColor(255, 255, 255, 200))
        grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
        p.setBrush(QtGui.QBrush(grad))
        p.setPen(QtCore.Qt.NoPen)
        p.drawRect(0, 0, 54, 54)
        p.end()
        self.shape_preview.setPixmap(pm)

        pm2 = QtGui.QPixmap(54, 54)
        pm2.fill(QtGui.QColor(16, 16, 16))
        p2 = QtGui.QPainter(pm2)
        for y in range(54):
            for x in range(54):
                val = max(0, min(255, int(127 + 100 * math.sin(x * 0.3) * math.cos(y * 0.3))))
                p2.setPen(QtGui.QColor(val, val, val))
                p2.drawPoint(x, y)
        p2.end()
        self.heightmap_preview.setPixmap(pm2)

    def _init_stroke_preview(self):
        self.stroke_preview.update_brush_state(
            size=60.0, opacity=1.0, hardness=1.0, color=[0.0, 0.0, 0.0]
        )

    # ── Theme ─────────────────────────────────────────────────────────
    def _apply_theme(self, _=""):
        from ui.core.theme.manager import ThemeManager
        tm = ThemeManager.instance()
        bg, bg2, bg3 = tm.get_color("bg_base"), tm.get_color("bg_elevated"), tm.get_color("bg_widget")
        text, muted, accent, border = tm.get_color("text_main"), tm.get_color("text_muted"), tm.get_color("accent"), tm.get_color("border")

        for sl in self._quick_sliders:
            sl.apply_theme(bg3, border, accent, text)

        self.setStyleSheet(f"""
            BrushSettingsDialog {{ background: {bg}; border: 1px solid {border}; border-radius: 8px; }}
            #BTitleBar {{ background: {bg2}; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
            #BTitleLabel {{ color: {text}; font-weight: 700; font-size: 12px; }}
            #BTitleIcon {{ font-size: 14px; padding-right: 2px; }}
            #BCloseBtn {{ background: transparent; color: {muted}; border: 1px solid {border}; border-radius: 3px; padding: 0 10px; font-size: 10px; }}
            #BCloseBtn:hover {{ background: {accent}; color: {text}; border-color: {accent}; }}
            #BSep, #BDivider {{ color: {border}; }}
            #BToolCol {{ background: {bg2}; border-bottom-left-radius: 8px; }}
            QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 6px; }}
            QToolButton:hover {{ background: {bg}; border-color: {border}; }}
            QToolButton:checked {{ background: {accent}; border-color: {accent}; }}
            #BProps {{ background: {bg}; border-bottom-right-radius: 8px; }}
            #BPresetLabel {{ color: {text}; font-size: 11px; font-weight: 600; background: {bg2}; border: 1px solid {border}; border-radius: 4px; padding: 4px 8px; }}
            #BAdvBtn {{ background: {bg2}; border: 1px solid {border}; border-radius: 4px; font-size: 13px; color: {text}; }}
            #BAdvBtn:hover {{ background: {accent}; border-color: {accent}; }}
            #BStrokePreview {{ border-radius: 6px; }}
            #BTexLabel {{ color: {muted}; font-size: 10px; }}
            #BTexPreview {{ border: 1px solid {border}; border-radius: 4px; background: {bg2}; }}
            #BTexBtn {{ background: {bg2}; color: {text}; border: 1px solid {border}; border-radius: 3px; font-size: 10px; padding: 0 4px; }}
            #BTexBtn:hover {{ border-color: {accent}; color: {accent}; }}
            #BSectionLabel {{ color: {muted}; font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }}
        """)

