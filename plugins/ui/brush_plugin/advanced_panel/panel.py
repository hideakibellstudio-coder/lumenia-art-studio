"""AdvancedPanel Dialog for Brush Settings and Engine Dynamics."""

import math
import logging
from PySide6 import QtWidgets, QtCore, QtGui

from .engine_params_widget import DynamicEngineParamsWidget
from .sections.size_opacity_section import create_size_opacity_section
from .sections.tip_geometry_section import create_tip_geometry_section
from .sections.jitters_section import create_jitters_section
from .sections.brush_texture_section import create_brush_texture_section, create_spacing_section
from .panel_engine_bridge import PanelEngineBridgeMixin

logger = logging.getLogger(__name__)

class AdvancedPanel(QtWidgets.QDialog, PanelEngineBridgeMixin):
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

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & QtCore.Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def show_near(self, anchor_widget: QtWidgets.QWidget):
        top = anchor_widget.window()
        workspace = getattr(top, "workspace", None) if top else None
        left_dock = getattr(workspace, "left_dock", None) if workspace else None

        scr = anchor_widget.screen().availableGeometry()

        if workspace and left_dock and hasattr(workspace, "workspace_area"):
            dock_right = getattr(left_dock, "effective_right_x", left_dock.mapToGlobal(QtCore.QPoint(left_dock.width(), 0)).x())
            workspace_global = workspace.workspace_area.mapToGlobal(QtCore.QPoint(0, 0))
            x = dock_right + 10
            y = workspace_global.y() + 10
            target_h = workspace.workspace_area.height() - 20
        else:
            top_left = anchor_widget.mapToGlobal(QtCore.QPoint(0, 0))
            dock_right = top_left.x() + anchor_widget.width()
            x = dock_right + 10
            y = top_left.y()
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

        from ui.core.i18n import tr, I18nManager

        self.tab_bar = QtWidgets.QTabBar()
        self.tab_bar.setExpanding(True)
        self.tab_bar.addTab(tr("tools.brush", "Pincel").split()[0])
        self.tab_bar.addTab(tr("brush.engine_dynamics", "Dinâmica por Motor"))
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

        # Page 0: Pincel
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

        # Page 1: Dinâmica por Motor
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
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def retranslate_ui(self):
        from ui.core.i18n import tr
        self.setWindowTitle(tr("brush.advanced_settings", "Configurações Avançadas"))
        if hasattr(self, "tab_bar"):
            self.tab_bar.setTabText(0, tr("tools.brush", "Pincel").split()[0])
            self.tab_bar.setTabText(1, tr("brush.engine_dynamics", "Dinâmica por Motor"))
        if hasattr(self, "lbl_title"):
            self.lbl_title.setText(tr("brush.advanced_title", "CONFIGURAÇÕES AVANÇADAS DE PINCEL"))

    def set_active_engine_type(self, engine_type: int):
        if hasattr(self, "dyn_params_widget"):
            self.dyn_params_widget.set_engine_type(engine_type)

    def _make_title_bar(self) -> QtWidgets.QWidget:
        from ui.core.icons import get_icon
        from ui.core.i18n import tr
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

        self.lbl_title = QtWidgets.QLabel(tr("brush.advanced_title", "CONFIGURAÇÕES AVANÇADAS DE PINCEL"))
        self.lbl_title.setObjectName("AdvTitleLabel")

        self.btn_close = QtWidgets.QToolButton()
        self.btn_close.setObjectName("AdvCloseBtn")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setIconSize(QtCore.QSize(12, 12))
        self.btn_close.setIcon(get_icon("close"))
        self.btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide)

        lo.addWidget(icon)
        lo.addWidget(self.lbl_title)
        lo.addStretch()
        lo.addWidget(self.btn_close)
        return bar

    def _build_brush_page(self, layout: QtWidgets.QVBoxLayout):
        layout.addWidget(create_size_opacity_section(self))
        layout.addWidget(create_tip_geometry_section(self))
        layout.addWidget(create_jitters_section(self))
        layout.addWidget(create_brush_texture_section(self))
        layout.addWidget(create_spacing_section(self))

    def sync_from_engine_profile(self):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if not b:
            return

        prof = b.get_brush_profile_dict()
        engine_type = b.get_active_engine_type()

        self.set_active_engine_type(engine_type)

        widgets_to_block = [
            getattr(self, "slider_size", None),
            getattr(self, "sl_min_size", None),
            getattr(self, "slider_opacity", None),
            getattr(self, "sl_min_op", None),
            getattr(self, "cmb_blend", None),
            getattr(self, "chk_vel_size", None),
            getattr(self, "chk_stroke_taper", None),
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
                self.slider_size.setValue(int(prof.get("brush_size", 20.0)))
            if hasattr(self, "sl_min_size"):
                self.sl_min_size.setValue(int(prof.get("min_size_percent", 0.0) * 100))
            if hasattr(self, "slider_opacity"):
                self.slider_opacity.setValue(int(prof.get("opacity", 1.0) * 100))
            if hasattr(self, "sl_min_op"):
                self.sl_min_op.setValue(int(prof.get("min_opacity_percent", 0.0) * 100))
            if hasattr(self, "cmb_blend"):
                bm_val = int(prof.get("blend_mode", 0))
                self.cmb_blend.setCurrentIndex(min(bm_val, self.cmb_blend.count() - 1))
            if hasattr(self, "chk_vel_size"):
                self.chk_vel_size.setChecked(bool(prof.get("velocity_size_enabled", False)))
            if hasattr(self, "chk_stroke_taper"):
                self.chk_stroke_taper.setChecked(bool(prof.get("stroke_taper_enabled", True)))
            if hasattr(self, "slider_stabilizer"):
                self.slider_stabilizer.setValue(int(prof.get("stabilizer_weight", 0.0) * 100 if prof.get("stabilizer_weight", 0.0) <= 1.0 else prof.get("stabilizer_weight", 0.0)))
            if hasattr(self, "sl_hardness"):
                self.sl_hardness.setValue(int(prof.get("hardness", 0.85) * 100))
            if hasattr(self, "sl_angle"):
                self.sl_angle.setValue(int(prof.get("tip_angle", 0.0)))
            if hasattr(self, "sl_press_angle"):
                self.sl_press_angle.setValue(int(prof.get("pressure_to_angle", 0.0)))
            if hasattr(self, "sl_aspect"):
                self.sl_aspect.setValue(int(prof.get("tip_aspect", 1.0) * 100))
            if hasattr(self, "chk_follow"):
                self.chk_follow.setChecked(bool(prof.get("follow_stroke", False)))
            if hasattr(self, "sl_jit_size"):
                self.sl_jit_size.setValue(int(prof.get("jitter_size", 0.0) * 100))
            if hasattr(self, "sl_jit_angle"):
                self.sl_jit_angle.setValue(int(prof.get("jitter_angle", 0.0) * 100))
            if hasattr(self, "sl_jit_pos"):
                self.sl_jit_pos.setValue(int(prof.get("jitter_position", 0.0) * 100))
            if hasattr(self, "chk_b_grain"):
                self.chk_b_grain.setChecked(bool(prof.get("brush_grain_enabled", False)))
            if hasattr(self, "sl_b_scale"):
                self.sl_b_scale.setValue(int(prof.get("brush_grain_scale", 1.0) * 100))
            if hasattr(self, "slider_contrast"):
                self.slider_contrast.setValue(int(prof.get("brush_grain_contrast", 1.0) * 100))
            if hasattr(self, "chk_invert"):
                self.chk_invert.setChecked(bool(prof.get("brush_grain_invert", False)))
            if hasattr(self, "slider_spacing"):
                self.slider_spacing.setValue(int(prof.get("spacing_factor", 0.08) * 100))
        finally:
            for w in widgets_to_block:
                if w:
                    w.blockSignals(False)

        self.update_shape_preview_from_engine()
        self.update_brush_height_preview_from_engine()

    def _apply_theme(self, _=""):
        from ui.core.icons import get_icon
        from ui.core.theme.manager import ThemeManager

        text = ThemeManager.instance().get_color("text_main")
        self.btn_close.setIcon(get_icon("close", text))
