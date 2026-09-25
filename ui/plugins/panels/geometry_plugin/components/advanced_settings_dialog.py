"""Advanced Geometry Dialog padronizado no Design System do Lumenia V2.

Modularizado sob ARCcC v2 (< 300 LOC).
"""

from __future__ import annotations

from typing import Optional
from PySide6 import QtWidgets, QtCore
from ui.infrastructure.theme.manager import ThemeManager
from ui.infrastructure.icons import get_icon
from ui.core.dialogs.floating_panel_window import CanvasAreaProvider, FloatingPanelWindow

from .curvilinear_perspective_page import CurvilinearPerspectivePage
from .snapping_guides_page import SnappingGuidesPage
from .symmetry_settings_page import SymmetrySettingsPage


class AdvancedGeometryDialog(FloatingPanelWindow):
    """Janela flutuante avançada padronizada com abas, aberturas colapsáveis e sliders compactos."""

    # Só os campos editados (ver `_on_changed`).
    settingsChanged = QtCore.Signal(dict)

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        current_state: Optional[dict] = None,
        canvas_area: Optional[CanvasAreaProvider] = None,
    ) -> None:
        super().__init__(canvas_area, parent)
        self.setWindowTitle("Configurações Avançadas de Geometria")
        self.setMinimumWidth(330)
        self.setMinimumHeight(460)

        self.state = current_state.copy() if current_state else {}
        self._build_ui()
        self._shown = self._collect()

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

    def show_near(self, anchor_widget: QtWidgets.QWidget) -> None:
        """Abre na borda do canvas do lado do botão (base FloatingPanelWindow)."""
        self.show_beside_canvas(anchor_widget, min_height=440)

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
        from ui.infrastructure.i18n import tr, I18nManager
        self.btn_reset = QtWidgets.QPushButton(tr("dialogs.reset_defaults", "Restaurar Padrões"))
        self.btn_reset.setObjectName("AdvResetBtn")
        self.btn_reset.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._on_reset)
        fl.addWidget(self.btn_reset)
        outer.addWidget(footer)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

    def retranslate_ui(self):
        from ui.infrastructure.i18n import tr
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

        from ui.infrastructure.i18n import tr
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

    def _pages(self):
        return (self.curv_page, self.snap_page, self.sym_page)

    def _collect(self) -> dict:
        values: dict = {}
        for page in self._pages():
            page.collect_state(values)
        return values

    def _show(self, state: dict) -> None:
        """Põe `state` nos widgets sem emitir e lembra o que ficou na tela."""
        widgets = [w for page in self._pages() for w in page.all_input_widgets()]
        for w in widgets:
            w.blockSignals(True)
        try:
            for page in self._pages():
                page.sync_from_state(state)
        finally:
            for w in widgets:
                w.blockSignals(False)
        self._shown = self._collect()

    def _on_changed(self) -> None:
        """Publica só os campos cujo widget o usuário mudou.

        Até 2026-09-24 publicava o dicionário inteiro: mudar os segmentos
        reescrevia o ângulo com o valor de quando o diálogo abriu, desfazendo o
        arrasto da alça no canvas. Quem liga uma régua ou simetria quando a aba
        editada não teria efeito é o `GeometryState.apply_advanced`.
        """
        now = self._collect()
        changed = {key: value for key, value in now.items() if self._shown.get(key) != value}
        self._shown = now
        if changed:
            self.state.update(changed)
            self.settingsChanged.emit(changed)

    def sync_from_state(self, state: dict) -> None:
        """Mostra o estado atual (não emite)."""
        self.state.update(state)
        self._show(self.state)

    def _on_reset(self) -> None:
        before = self._shown
        self._show({**self.state, **{
            "yaw": 0.0, "pitch": 0.0, "fov": 130.0, "density": 30.0,
            "show_ring": True, "show_straight_verticals": False, "show_v": True, "show_vps": False,
            "show_h": True, "show_letterbox": False, "show_d": True, "show_cube": False,
            "show_ground": False, "show_ceiling": False, "show_ground_verticals": False,
            "show_ceiling_verticals": False, "aspect_ratio": "16:9", "snap_mode": "auto",
            "snap_sensitivity": 3.0, "snap_dynamic": True, "show_hint": True, "hidden": False,
            "segments": 6, "angle": 90.0, "stop_at_center": False, "locked": False
        }})
        self._shown = before  # o que o reset mudou na tela conta como editado
        self._on_changed()

    def _apply_theme(self, _="") -> None:
        from ui.infrastructure.icons import get_icon
        from ui.infrastructure.theme.manager import ThemeManager

        text = ThemeManager.instance().get_color("text_main")
        self.btn_close.setIcon(get_icon("close", text))
