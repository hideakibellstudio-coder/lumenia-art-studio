"""AdvancedPanel — janela de ajustes avançados do pincel.

Duas abas: "Pincel" (cinco seções com estado próprio, em `sections/`) e
"Dinâmica por Motor" (`DynamicEngineParamsWidget`). Parâmetros rápidos vão
ao `BrushState`; os avançados, ao motor pelo `BrushEngineWriter`.

Até 2026-09-24 as seções eram funções que penduravam ~25 widgets neste
painel, um mixin (`PanelEngineBridgeMixin`) escrevia no motor relendo esses
widgets, e `sync_from_engine_profile` testava cada um com `hasattr`.
"""

import logging
from typing import Optional

from PySide6 import QtWidgets, QtCore

from ui.core.dialogs.floating_panel_window import CanvasAreaProvider, FloatingPanelWindow
from ui.core.engine.registry import EngineRegistry
from ui.core.state import BrushParam, BrushState

from .brush_engine_writer import BrushEngineWriter
from .engine_params_widget import DynamicEngineParamsWidget
from .sections.brush_texture_section import BrushTextureSection, SpacingSection
from .sections.jitters_section import JittersSection
from .sections.size_opacity_section import SizeOpacitySection
from .sections.tip_geometry_section import TipGeometrySection

logger = logging.getLogger(__name__)


class AdvancedPanel(FloatingPanelWindow):
    """Janela flutuante com todos os parâmetros do pincel."""

    # (nome do pin, fixado?) -> o painel principal mostra/esconde o slider rápido.
    pinToggled = QtCore.Signal(str, bool)

    def __init__(self, brush_state: BrushState, canvas_area: Optional[CanvasAreaProvider] = None, parent=None):
        super().__init__(canvas_area, parent)
        self.setWindowTitle("Configurações Avançadas")
        self.setMinimumWidth(330)
        self.setMinimumHeight(440)

        self._state = brush_state
        self._writer = BrushEngineWriter(EngineRegistry.instance().get_backend)
        self.sections = (
            SizeOpacitySection(brush_state, self._writer),
            TipGeometrySection(brush_state, self._writer),
            JittersSection(brush_state, self._writer),
            BrushTextureSection(brush_state, self._writer),
            SpacingSection(brush_state, self._writer),
        )
        for section in self.sections:
            section.pinToggled.connect(self.pinToggled)
        self._build_ui()
        brush_state.paramChanged.connect(self._on_state_param_changed)
        self._show_state()

        from ui.infrastructure.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme("")

    # ── Estado e motor → tela ─────────────────────────────────────────────

    def _on_state_param_changed(self, param: BrushParam, value) -> None:
        for section in self.sections:
            section.show_param(param, value)

    def _show_state(self) -> None:
        for param, value in self._state.snapshot().items():
            self._on_state_param_changed(param, value)

    def sync_from_engine_profile(self) -> None:
        """Mostra o perfil do motor (preset trocado, janela reaberta)."""
        profile = self._writer.profile()
        if profile is None:
            return
        self.dyn_params_widget.set_engine_type(self._writer.engine_type())
        for section in self.sections:
            section.show_profile(profile)
        # Os parâmetros rápidos seguem o BrushState (o perfil do motor não
        # guarda o estabilizador, por exemplo).
        self._show_state()

    def show_near(self, anchor_widget: QtWidgets.QWidget) -> None:
        self.show_beside_canvas(anchor_widget, min_height=420)

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

        from ui.infrastructure.i18n import tr, I18nManager

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

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def retranslate_ui(self):
        from ui.infrastructure.i18n import tr
        self.setWindowTitle(tr("brush.advanced_settings", "Configurações Avançadas"))
        self.tab_bar.setTabText(0, tr("tools.brush", "Pincel").split()[0])
        self.tab_bar.setTabText(1, tr("brush.engine_dynamics", "Dinâmica por Motor"))
        self.lbl_title.setText(tr("brush.advanced_title", "CONFIGURAÇÕES AVANÇADAS DE PINCEL"))

    def _make_title_bar(self) -> QtWidgets.QWidget:
        from ui.infrastructure.icons import get_icon
        from ui.infrastructure.i18n import tr
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
        for section in self.sections:
            layout.addWidget(section)

    def _on_tab(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def _apply_theme(self, _=""):
        from ui.infrastructure.icons import get_icon
        from ui.infrastructure.theme.manager import ThemeManager

        text = ThemeManager.instance().get_color("text_main")
        self.btn_close.setIcon(get_icon("close", text))
