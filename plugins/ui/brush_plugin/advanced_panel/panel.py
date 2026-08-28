"""AdvancedPanel Dialog for Brush Settings and Engine Dynamics."""

import math
import logging
from PySide6 import QtWidgets, QtCore, QtGui

from .engine_params_widget import DynamicEngineParamsWidget
from .sections.size_opacity_section import create_size_opacity_section
from .sections.tip_geometry_section import create_tip_geometry_section
from .sections.jitters_section import create_jitters_section
from .sections.brush_texture_section import create_brush_texture_section, create_spacing_section

logger = logging.getLogger(__name__)

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
        layout.addWidget(create_size_opacity_section(self))
        layout.addWidget(create_tip_geometry_section(self))
        layout.addWidget(create_jitters_section(self))
        layout.addWidget(create_brush_texture_section(self))
        layout.addWidget(create_spacing_section(self))

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
                    self.slider_stabilizer.setValue(int(stab.get_stabilization_percentage()))
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

    def _on_vel_size(self, _s):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_brush_profile().velocity_size_enabled = bool(self.chk_vel_size.isChecked())

    def _on_stabilizer_changed(self, v):
        from ui.core.engine.registry import EngineRegistry
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "_facade") and b._facade:
            b._facade.get_stabilizer().set_stabilization_percentage(float(v))
        self.stabilizerWeightChanged.emit(float(v) / 100.0)

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

    def _on_b_grain_enabled(self, _s):
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

    def _on_tip_follow(self, _s):
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
        from .panel_thumbnails import create_default_shape_pixmap, create_default_grain_pixmap
        if hasattr(self, "shape_preview"):
            self.shape_preview.setPixmap(create_default_shape_pixmap())
        if hasattr(self, "preview_b_grain"):
            self.preview_b_grain.setPixmap(create_default_grain_pixmap())

    def _apply_theme(self, _=""):
        from ui.core.icons import get_icon
        from ui.core.theme.manager import ThemeManager

        text = ThemeManager.instance().get_color("text_main")
        self.btn_close.setIcon(get_icon("close", text))
