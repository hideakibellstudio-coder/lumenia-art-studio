"""Advanced Geometry Dialog padronizado no Design System do Lumenia V2.

Modularizado sob ARCcC v2 (< 300 LOC).
"""

from __future__ import annotations

from typing import Optional
from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon

from .curvilinear_perspective_page import CurvilinearPerspectivePage
from .snapping_guides_page import SnappingGuidesPage
from .symmetry_settings_page import SymmetrySettingsPage


class AdvancedGeometryDialog(QtWidgets.QDialog):
    """Janela flutuante avançada padronizada com abas, aberturas colapsáveis e sliders compactos."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, current_state: Optional[dict] = None) -> None:
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

    # ── Retrocompatibilidade de Atributos e Widgets Delegados ─────────────
    # Página 0: Perspectiva Curvilínea 6P
    @property
    def sec_cam(self): return self.curv_page.sec_cam
    @property
    def slider_yaw(self): return self.curv_page.slider_yaw
    @property
    def slider_pitch(self): return self.curv_page.slider_pitch
    @property
    def slider_fov(self): return self.curv_page.slider_fov
    @property
    def sec_grid(self): return self.curv_page.sec_grid
    @property
    def lbl_d(self): return self.curv_page.lbl_d
    @property
    def combo_density(self): return self.curv_page.combo_density
    @property
    def lbl_a(self): return self.curv_page.lbl_a
    @property
    def combo_aspect(self): return self.curv_page.combo_aspect
    @property
    def chk_ring(self): return self.curv_page.chk_ring
    @property
    def chk_straight_v(self): return self.curv_page.chk_straight_v
    @property
    def chk_v(self): return self.curv_page.chk_v
    @property
    def chk_vps(self): return self.curv_page.chk_vps
    @property
    def chk_h(self): return self.curv_page.chk_h
    @property
    def chk_letterbox(self): return self.curv_page.chk_letterbox
    @property
    def chk_d(self): return self.curv_page.chk_d
    @property
    def chk_cube(self): return self.curv_page.chk_cube
    @property
    def chk_ground(self): return self.curv_page.chk_ground
    @property
    def chk_ceiling(self): return self.curv_page.chk_ceiling
    @property
    def chk_ground_v(self): return self.curv_page.chk_ground_v
    @property
    def chk_ceiling_v(self): return self.curv_page.chk_ceiling_v

    # Página 1: Snapping & Guias
    @property
    def sec_snap(self): return self.snap_page.sec_snap
    @property
    def lbl_m(self): return self.snap_page.lbl_m
    @property
    def combo_snap_mode(self): return self.snap_page.combo_snap_mode
    @property
    def slider_sens(self): return self.snap_page.slider_sens
    @property
    def sec_draw(self): return self.snap_page.sec_draw
    @property
    def chk_dynamic(self): return self.snap_page.chk_dynamic
    @property
    def chk_hint(self): return self.snap_page.chk_hint
    @property
    def chk_hide(self): return self.snap_page.chk_hide

    # Página 2: Simetria
    @property
    def sec_axes(self): return self.sym_page.sec_axes
    @property
    def slider_seg(self): return self.sym_page.slider_seg
    @property
    def slider_ang(self): return self.sym_page.slider_ang
    @property
    def sec_rest(self): return self.sym_page.sec_rest
    @property
    def chk_stop(self): return self.sym_page.chk_stop
    @property
    def chk_lock(self): return self.sym_page.chk_lock

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
        right_dock = getattr(workspace, "right_dock", None) if workspace else None

        scr = anchor_widget.screen().availableGeometry() if anchor_widget.screen() else QtCore.QRect(0, 0, 1920, 1080)
        anchor_global = anchor_widget.mapToGlobal(QtCore.QPoint(0, 0))
        is_on_right = anchor_global.x() > scr.center().x()

        if workspace and (right_dock or left_dock):
            workspace_global = workspace.workspace_area.mapToGlobal(QtCore.QPoint(0, 0))
            target_h = max(440, workspace.workspace_area.height() - 20)
            y = workspace_global.y() + 10

            if is_on_right and right_dock:
                dock_left = getattr(right_dock, "effective_left_x", right_dock.mapToGlobal(QtCore.QPoint(0, 0)).x())
                x = dock_left - self.width() - 10
            elif left_dock:
                dock_right = getattr(left_dock, "effective_right_x", left_dock.mapToGlobal(QtCore.QPoint(left_dock.width(), 0)).x())
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

        # Três abas especializadas sob ARCcC v2
        self.curv_page = CurvilinearPerspectivePage(self, self.state)
        self.curv_page.changed.connect(self._on_changed)
        self.stack.addWidget(self.curv_page)

        self.snap_page = SnappingGuidesPage(self, self.state)
        self.snap_page.changed.connect(self._on_changed)
        self.stack.addWidget(self.snap_page)

        self.sym_page = SymmetrySettingsPage(self, self.state)
        self.sym_page.changed.connect(self._on_changed)
        self.stack.addWidget(self.sym_page)

        for widget_type in (QtWidgets.QComboBox, QtWidgets.QSlider, QtWidgets.QSpinBox):
            for w in self.findChildren(widget_type):
                w.installEventFilter(self)

        footer = QtWidgets.QWidget()
        fl = QtWidgets.QHBoxLayout(footer)
        from ui.core.i18n import tr, I18nManager
        self.btn_reset = QtWidgets.QPushButton(tr("dialogs.reset_defaults", "Restaurar Padrões"))
        self.btn_reset.setObjectName("AdvResetBtn")
        self.btn_reset.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._on_reset)
        fl.addWidget(self.btn_reset)
        outer.addWidget(footer)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

    def retranslate_ui(self):
        from ui.core.i18n import tr
        self.setWindowTitle(tr("geometry.advanced_dialog_title", "Configurações Avançadas de Geometria"))
        if hasattr(self, "lbl_title"):
            self.lbl_title.setText(tr("geometry.advanced_title", "CONFIGURAÇÕES AVANÇADAS DE GEOMETRIA"))
        if hasattr(self, "btn_reset"):
            self.btn_reset.setText(tr("dialogs.reset_defaults", "Restaurar Padrões"))
        if hasattr(self, "tab_bar"):
            self.tab_bar.setTabText(0, tr("geometry.tab_persp6p", "Perspectiva 6P"))
            self.tab_bar.setTabText(1, tr("geometry.tab_snapping", "Snapping & Guias"))
            self.tab_bar.setTabText(2, tr("geometry.tab_symmetry", "Simetria"))

        if hasattr(self, "curv_page"):
            self.curv_page.retranslate_ui()
        if hasattr(self, "snap_page"):
            self.snap_page.retranslate_ui()
        if hasattr(self, "sym_page"):
            self.sym_page.retranslate_ui()

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Wheel:
            if isinstance(watched, (QtWidgets.QComboBox, QtWidgets.QSlider, QtWidgets.QSpinBox)):
                event.ignore()
                return True
        return super().eventFilter(watched, event)

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

        from ui.core.i18n import tr
        self.lbl_title = QtWidgets.QLabel(tr("geometry.advanced_title", "CONFIGURAÇÕES AVANÇADAS DE GEOMETRIA"))
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

    def _on_tab(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)

    def _on_changed(self) -> None:
        self.curv_page.collect_state(self.state)
        self.snap_page.collect_state(self.state)
        self.sym_page.collect_state(self.state)

        # Auto-ativação se nenhuma régua / simetria estiver ativa
        if self.stack.currentIndex() == 0 and self.state.get("ruler_type") == "none":
            self.state["ruler_type"] = "curvilinear"
            self.state["ruler_idx"] = 6

        if self.stack.currentIndex() == 2 and self.state.get("sym_type") == "none":
            self.state["sym_type"] = "radial"
            self.state["sym_idx"] = 4

        self.settingsChanged.emit(self.state)

    def sync_from_state(self, state: dict) -> None:
        self.state.update(state)
        all_widgets = (
            self.curv_page.all_input_widgets()
            + self.snap_page.all_input_widgets()
            + self.sym_page.all_input_widgets()
        )
        for w in all_widgets:
            w.blockSignals(True)
        try:
            self.curv_page.sync_from_state(self.state)
            self.snap_page.sync_from_state(self.state)
            self.sym_page.sync_from_state(self.state)
        finally:
            for w in all_widgets:
                w.blockSignals(False)

    def _on_reset(self) -> None:
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

    def _apply_theme(self, _="") -> None:
        from ui.core.icons import get_icon
        from ui.core.theme.manager import ThemeManager

        text = ThemeManager.instance().get_color("text_main")
        self.btn_close.setIcon(get_icon("close", text))
