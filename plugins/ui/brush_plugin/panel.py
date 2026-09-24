"""
BrushSettingsPanel — painel de pincel e ferramentas (plugin BrushPlugin)
========================================================================
Seleção de preset, prévia do traço, parâmetros rápidos e opções contextuais
de cada ferramenta.

Contrato (desde 2026-09-24):
- recebe o `BrushState` pelo construtor e é uma VIEW dele: os sliders escrevem
  no estado e se atualizam pelos sinais do estado. O painel não fala com o
  motor sobre cor/tamanho/opacidade/... — quem faz isso é o BrushEngineSync.
- nenhum outro componente lê ou escreve os widgets internos deste painel.
  O que sai daqui para fora sai por sinal público (`toolActivated`,
  `toolOptionsChanged`).
"""

from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.i18n import I18nManager, tr
from ui.core.icons import get_icon
from ui.core.state import BrushParam, BrushState
from ui.core.theme.manager import ThemeManager
from ui.core.widgets.card_box import PanelCardBox
from ui.core.widgets.tool_options_widgets import (
    EyedropOptionsWidget,
    BucketOptionsWidget,
    WandOptionsWidget,
    TransformOptionsWidget,
    SelectionOptionsWidget,
    ShapesOptionsWidget,
)

from .advanced_panel import AdvancedPanel
from .brush_dropdown import BrushDropdown
from .components import ToolSelectionColumn, QuickSlidersSection
from .stroke_preview import StrokePreview

_BRUSH_PAGE_TOOLS = ("brush", "eraser", "smudge")
_SELECTION_TOOLS = ("rect_select", "ellipse_select", "lasso")


class BrushSettingsPanel(QtWidgets.QWidget):
    """Painel isolado contendo as Configurações do Pincel e Ferramentas."""

    toolActivated = QtCore.Signal(str)
    toolOptionsChanged = QtCore.Signal(str, dict)

    def __init__(self, brush_state: BrushState, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BrushSettingsPanel")
        self._state = brush_state
        self._adv_panel: Optional[AdvancedPanel] = None
        self._active_tool_id = "brush"

        self._build_ui()

        brush_state.paramChanged.connect(self._on_param_changed)
        brush_state.colorChanged.connect(self._on_color_changed)
        brush_state.presetSelected.connect(self._on_preset_selected)
        for param, value in brush_state.snapshot().items():
            self._on_param_changed(param, value)
        self._on_color_changed(brush_state.color)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme_style)
        self._apply_theme_style()
        # O preset inicial é aplicado depois do primeiro ciclo de eventos: o
        # motor só existe depois que o workspace inicializa. O timer é preso ao
        # painel para não disparar se ele for destruído antes.
        QtCore.QTimer.singleShot(0, self, self.sync_initial_state)

    # ── Estado → view ─────────────────────────────────────────────────────

    def sync_initial_state(self) -> None:
        self.preset_combo.sync_to_tool("brush")

    def _on_param_changed(self, param: BrushParam, value) -> None:
        if isinstance(value, bool):
            return  # parâmetros booleanos só aparecem no painel avançado
        self.sliders_section.show_value(param, value)
        if param is BrushParam.SIZE:
            self.stroke_preview.update_brush_state(size=value)
        elif param is BrushParam.OPACITY:
            self.stroke_preview.update_brush_state(opacity=value)
        elif param is BrushParam.SPACING:
            self.stroke_preview.update_brush_state(spacing=value)
        elif param is BrushParam.PRESSURE:
            self.stroke_preview.update_brush_state(pressure=value)
        elif param is BrushParam.CONTRAST:
            self.stroke_preview.update_brush_state(hardness=min(0.99, max(0.01, value / 3.0)))

    def _on_color_changed(self, color: QtGui.QColor) -> None:
        self.stroke_preview.update_brush_state(color=[color.redF(), color.greenF(), color.blueF()])
        self.eyedrop_options_widget.set_captured_color(color)
        self.shapes_options_widget.set_active_color(color)

    def _on_preset_selected(self, _tool_id: str, _name: str, data: dict) -> None:
        self.stroke_preview.update_brush_state(
            hardness=data.get("hardness", 0.85),
            engine_type=data.get("engine_type", 0),
        )
        if self._adv_panel is not None:
            self._adv_panel.sync_from_engine_profile()

    # ── View → estado ─────────────────────────────────────────────────────

    def _on_slider_edited(self, param: BrushParam, value: float) -> None:
        self._state.set_value(param, value)

    # ── Ferramentas ───────────────────────────────────────────────────────

    def set_tool_active(self, tool_name: str) -> None:
        self._active_tool_id = tool_name
        self.tool_column.set_tool_active(tool_name)
        self.preset_combo.sync_to_tool(tool_name)
        if tool_name.startswith("shape_"):
            self.shapes_options_widget.set_active_shape_type(tool_name)
        self.stacked_tool_props.setCurrentWidget(self._options_page_for(tool_name))

    def _options_page_for(self, tool_name: str) -> QtWidgets.QWidget:
        if tool_name in _BRUSH_PAGE_TOOLS:
            return self.brush_props_widget
        if tool_name in _SELECTION_TOOLS:
            return self.selection_options_widget
        if tool_name == "shapes" or tool_name.startswith("shape_"):
            return self.shapes_options_widget
        pages = {
            "eyedrop": self.eyedrop_options_widget,
            "bucket": self.bucket_options_widget,
            "wand": self.wand_options_widget,
            "transform": self.transform_options_widget,
        }
        return pages.get(tool_name, self.brush_props_widget)

    def _on_tool(self, tool_id: str) -> None:
        self.set_tool_active(tool_id)
        self.toolActivated.emit(tool_id)
        if tool_id == "shapes":
            self.shapes_options_widget.emit_current_settings()

    def _on_selection_options_changed(self, settings: dict) -> None:
        tool = self._active_tool_id if self._active_tool_id in _SELECTION_TOOLS else "rect_select"
        self.toolOptionsChanged.emit(tool, settings)

    # ── Painel avançado ───────────────────────────────────────────────────

    def _toggle_advanced_panel(self) -> None:
        if self._adv_panel is None:
            self._adv_panel = AdvancedPanel(self._state, self)
            self._adv_panel.pinToggled.connect(self.sliders_section.set_pinned_visible)
        if self._adv_panel.isVisible():
            self._adv_panel.hide()
        else:
            self._adv_panel.sync_from_engine_profile()
            self._adv_panel.show_near(self.btn_adv)

    # ── Construção ────────────────────────────────────────────────────────

    def retranslate_ui(self) -> None:
        self.btn_adv.setToolTip(tr("brush.advanced_settings", "Configurações Avançadas do Pincel"))
        self.tool_column.retranslate_ui()
        self.sliders_section.retranslate_ui()

    def _build_ui(self) -> None:
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(0)

        content_widget = QtWidgets.QWidget()
        content_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        settings_layout = QtWidgets.QHBoxLayout(content_widget)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(4)

        self.tool_column = ToolSelectionColumn(self)
        self.tool_column.toolActivated.connect(self._on_tool)
        settings_layout.addWidget(self.tool_column)

        self.vline = QtWidgets.QFrame()
        self.vline.setFrameShape(QtWidgets.QFrame.VLine)
        self.vline.setObjectName("DockVLine")
        settings_layout.addWidget(self.vline)

        props_col = QtWidgets.QWidget()
        props_col.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        col_layout = QtWidgets.QVBoxLayout(props_col)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(0)

        self.stacked_tool_props = QtWidgets.QStackedWidget(props_col)
        self.stacked_tool_props.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.stacked_tool_props.addWidget(self._build_brush_page())
        self._build_option_pages()

        col_layout.addWidget(self.stacked_tool_props)
        settings_layout.addWidget(props_col, 1)

        card_box = PanelCardBox("", content_widget, self)
        card_box.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        main_layout.addWidget(card_box, 1)

    def _build_brush_page(self) -> QtWidgets.QWidget:
        self.brush_props_widget = QtWidgets.QWidget()
        props_layout = QtWidgets.QVBoxLayout(self.brush_props_widget)
        props_layout.setContentsMargins(0, 0, 0, 0)
        props_layout.setSpacing(5)

        row1 = QtWidgets.QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(4)

        self.preset_combo = BrushDropdown(self._state, self)
        self.preset_combo.setObjectName("BPresetCombo")
        self.preset_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.btn_adv = QtWidgets.QToolButton(self)
        self.btn_adv.setObjectName("DockAdvBtn")
        self.btn_adv.setIcon(get_icon("settings"))
        self.btn_adv.setIconSize(QtCore.QSize(16, 16))
        self.btn_adv.setFixedSize(26, 26)
        self.btn_adv.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_adv.clicked.connect(self._toggle_advanced_panel)

        row1.addWidget(self.preset_combo, 1)
        row1.addWidget(self.btn_adv)
        props_layout.addLayout(row1)

        self.stroke_preview = StrokePreview(self)
        self.stroke_preview.setFixedHeight(48)
        self.stroke_preview.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        props_layout.addWidget(self.stroke_preview)

        self.sliders_section = QuickSlidersSection(self)
        self.sliders_section.paramEdited.connect(self._on_slider_edited)
        props_layout.addWidget(self.sliders_section)
        return self.brush_props_widget

    def _build_option_pages(self) -> None:
        self.eyedrop_options_widget = EyedropOptionsWidget(self)
        self.bucket_options_widget = BucketOptionsWidget(self)
        self.wand_options_widget = WandOptionsWidget(self)
        self.transform_options_widget = TransformOptionsWidget(self)
        self.selection_options_widget = SelectionOptionsWidget(self)
        self.shapes_options_widget = ShapesOptionsWidget(self)

        forwarded = {
            "eyedrop": self.eyedrop_options_widget,
            "bucket": self.bucket_options_widget,
            "wand": self.wand_options_widget,
            "transform": self.transform_options_widget,
            "shapes": self.shapes_options_widget,
        }
        for tool_id, widget in forwarded.items():
            widget.settingsChanged.connect(lambda s, t=tool_id: self.toolOptionsChanged.emit(t, s))
        self.selection_options_widget.settingsChanged.connect(self._on_selection_options_changed)

        for widget in (
            self.eyedrop_options_widget, self.bucket_options_widget, self.wand_options_widget,
            self.transform_options_widget, self.selection_options_widget, self.shapes_options_widget,
        ):
            self.stacked_tool_props.addWidget(widget)

    def _apply_theme_style(self, *_args) -> None:
        theme = ThemeManager.instance()
        border = theme.get_color("border")
        text_primary = theme.get_color("text_main")
        accent = theme.get_color("accent")

        self.btn_adv.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: 1px solid {border};
                border-radius: 4px;
                color: {text_primary};
                font-size: 13px;
                font-weight: bold;
            }}
            QToolButton:hover {{
                border-color: {accent};
            }}
        """)

        self.vline.setStyleSheet(f"background-color: {border}; max-width: 1px;")
        self.tool_column.apply_theme_style(theme)
        self.sliders_section.apply_theme_style(theme)
