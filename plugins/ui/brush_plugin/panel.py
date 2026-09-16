"""
BrushSettingsPanel — Painel Isolado de Configurações de Pincéis & Ferramentas
=============================================================================
Painel individual contendo seleção de presets, preview do traço, parâmetros rápidos
e opções de ferramentas contextuais, envolvido na moldura padronizada PanelCardBox.

Modularizado sob ARCcC v2 (< 300 LOC).
"""

from __future__ import annotations

from typing import Dict, Optional
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.icons import get_icon
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

from .stroke_preview import StrokePreview
from .compact_slider import CompactSlider
from .advanced_panel import AdvancedPanel
from .brush_dropdown import BrushDropdown
from .components import ToolSelectionColumn, QuickSlidersSection

class BrushSettingsPanel(QtWidgets.QWidget):
    """Painel isolado contendo as Configurações do Pincel e Ferramentas."""

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
    toolActivated             = QtCore.Signal(str)
    toolOptionsChanged        = QtCore.Signal(str, dict)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BrushSettingsPanel")

        self._adv_panel: Optional[AdvancedPanel] = None

        self.setup_ui()

        from ui.core.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme_style)
        self._apply_theme_style()
        QtCore.QTimer.singleShot(0, self.sync_initial_state)

    # ── Retrocompatibilidade de Propriedades de Sliders e Colunas ─────────
    @property
    def qs_size(self) -> CompactSlider:
        return self.sliders_section.size_slider

    @property
    def qs_opacity(self) -> CompactSlider:
        return self.sliders_section.opacity_slider

    @property
    def size_slider(self) -> CompactSlider:
        return self.sliders_section.size_slider

    @property
    def opacity_slider(self) -> CompactSlider:
        return self.sliders_section.opacity_slider

    @property
    def contrast_slider(self) -> CompactSlider:
        return self.sliders_section.contrast_slider

    @property
    def pressure_slider(self) -> CompactSlider:
        return self.sliders_section.pressure_slider

    @property
    def curve_slider(self) -> CompactSlider:
        return self.sliders_section.curve_slider

    @property
    def stabilizer_slider(self) -> CompactSlider:
        return self.sliders_section.stabilizer_slider

    @property
    def spacing_slider(self) -> CompactSlider:
        return self.sliders_section.spacing_slider

    @property
    def min_density_slider(self) -> CompactSlider:
        return self.sliders_section.min_density_slider

    @property
    def lbl_quick(self) -> QtWidgets.QLabel:
        return self.sliders_section.lbl_quick

    @property
    def _quick_sliders(self):
        return self.sliders_section.all_sliders

    @property
    def _tool_buttons(self) -> Dict[str, QtWidgets.QToolButton]:
        return self.tool_column.tool_buttons

    @property
    def tool_col_box(self) -> ToolSelectionColumn:
        return self.tool_column

    def sync_initial_state(self) -> None:
        if hasattr(self, "preset_combo") and self.preset_combo:
            self.preset_combo.sync_to_tool("brush")

    def retranslate_ui(self) -> None:
        from ui.core.i18n import tr
        if hasattr(self, "btn_adv"):
            self.btn_adv.setToolTip(tr("brush.advanced_settings", "Configurações Avançadas do Pincel"))
        if hasattr(self, "tool_column"):
            self.tool_column.retranslate_ui()
        if hasattr(self, "sliders_section"):
            self.sliders_section.retranslate_ui()

    def setup_ui(self) -> None:
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(0)

        content_widget = QtWidgets.QWidget()
        content_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        settings_layout = QtWidgets.QHBoxLayout(content_widget)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(4)

        # Coluna vertical de ferramentas modularizada
        self.tool_column = ToolSelectionColumn(self)
        self.tool_column.toolActivated.connect(self._on_tool)
        settings_layout.addWidget(self.tool_column)

        # Divisor vertical
        self.vline = QtWidgets.QFrame()
        self.vline.setFrameShape(QtWidgets.QFrame.VLine)
        self.vline.setObjectName("DockVLine")
        settings_layout.addWidget(self.vline)

        # Painel central de propriedades empilhadas por ferramenta
        props_col = QtWidgets.QWidget()
        props_col.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        col_layout = QtWidgets.QVBoxLayout(props_col)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(0)

        self.stacked_tool_props = QtWidgets.QStackedWidget(props_col)
        self.stacked_tool_props.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # ── 1. Página de Pincéis & Parâmetros Rápidos ────────────────────────
        self.brush_props_widget = QtWidgets.QWidget()
        props_layout = QtWidgets.QVBoxLayout(self.brush_props_widget)
        props_layout.setContentsMargins(0, 0, 0, 0)
        props_layout.setSpacing(5)

        row1 = QtWidgets.QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(4)

        self.preset_combo = BrushDropdown(self)
        self.preset_combo.setObjectName("BPresetCombo")
        self.preset_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.preset_combo.preset_changed.connect(self._on_preset_changed)

        self.btn_adv = QtWidgets.QToolButton(self)
        self.btn_adv.setObjectName("DockAdvBtn")
        self.btn_adv.setIcon(get_icon("settings"))
        self.btn_adv.setIconSize(QtCore.QSize(16, 16))
        self.btn_adv.setToolTip("Configurações Avançadas do Pincel")
        self.btn_adv.setFixedSize(26, 26)
        self.btn_adv.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_adv.clicked.connect(self._open_advanced_dialog)

        row1.addWidget(self.preset_combo, 1)
        row1.addWidget(self.btn_adv)
        props_layout.addLayout(row1)

        self.stroke_preview = StrokePreview(self)
        self.stroke_preview.setFixedHeight(48)
        self.stroke_preview.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        props_layout.addWidget(self.stroke_preview)

        # Seção modularizada de sliders rápidos e pináveis
        self.sliders_section = QuickSlidersSection(self)
        self.sliders_section.sizeChanged.connect(self._on_size_changed)
        self.sliders_section.opacityChanged.connect(self._on_opacity_changed)
        self.sliders_section.contrastChanged.connect(self._on_contrast_changed)
        self.sliders_section.pressureChanged.connect(self.pressureChanged.emit)
        self.sliders_section.pressureCurvePowerChanged.connect(self.pressureCurvePowerChanged.emit)
        self.sliders_section.stabilizerWeightChanged.connect(self._on_stabilizer_changed)
        self.sliders_section.spacingChanged.connect(self._on_spacing_changed)
        self.sliders_section.minDensityValueChanged.connect(self.minDensityValueChanged.emit)
        props_layout.addWidget(self.sliders_section)

        self.stacked_tool_props.addWidget(self.brush_props_widget)

        # ── 2. Páginas de Opções de Ferramentas Específicas ─────────────────
        self.eyedrop_options_widget = EyedropOptionsWidget(self)
        self.eyedrop_options_widget.settingsChanged.connect(lambda s: self.toolOptionsChanged.emit("eyedrop", s))
        self.stacked_tool_props.addWidget(self.eyedrop_options_widget)

        self.bucket_options_widget = BucketOptionsWidget(self)
        self.bucket_options_widget.settingsChanged.connect(lambda s: self.toolOptionsChanged.emit("bucket", s))
        self.stacked_tool_props.addWidget(self.bucket_options_widget)

        self.wand_options_widget = WandOptionsWidget(self)
        self.wand_options_widget.settingsChanged.connect(lambda s: self.toolOptionsChanged.emit("wand", s))
        self.stacked_tool_props.addWidget(self.wand_options_widget)

        self.transform_options_widget = TransformOptionsWidget(self)
        self.transform_options_widget.settingsChanged.connect(lambda s: self.toolOptionsChanged.emit("transform", s))
        self.stacked_tool_props.addWidget(self.transform_options_widget)

        self.selection_options_widget = SelectionOptionsWidget(self)
        self.selection_options_widget.settingsChanged.connect(self._on_selection_options_changed)
        self.stacked_tool_props.addWidget(self.selection_options_widget)

        self.shapes_options_widget = ShapesOptionsWidget(self)
        self.shapes_options_widget.settingsChanged.connect(lambda s: self.toolOptionsChanged.emit("shapes", s))
        self.stacked_tool_props.addWidget(self.shapes_options_widget)

        col_layout.addWidget(self.stacked_tool_props)
        settings_layout.addWidget(props_col, 1)

        card_box = PanelCardBox("", content_widget, self)
        card_box.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        main_layout.addWidget(card_box, 1)

    def _apply_theme_style(self, *args) -> None:
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
        if hasattr(self, "tool_column"):
            self.tool_column.apply_theme_style(theme)
        if hasattr(self, "sliders_section"):
            self.sliders_section.apply_theme_style(theme)

    def set_tool_active(self, tool_name: str) -> None:
        self._active_tool_id = tool_name
        if hasattr(self, "tool_column"):
            self.tool_column.set_tool_active(tool_name)

        if hasattr(self, "preset_combo") and self.preset_combo:
            self.preset_combo.sync_to_tool(tool_name)

        if hasattr(self, "shapes_options_widget") and tool_name.startswith("shape_") and tool_name != "shapes":
            self.shapes_options_widget.set_active_shape_type(tool_name)

        if hasattr(self, "stacked_tool_props"):
            tool_to_widget = {
                "brush": self.brush_props_widget,
                "eraser": self.brush_props_widget,
                "smudge": self.brush_props_widget,
                "eyedrop": self.eyedrop_options_widget,
                "bucket": self.bucket_options_widget,
                "wand": self.wand_options_widget,
                "transform": self.transform_options_widget,
                "rect_select": self.selection_options_widget,
                "ellipse_select": self.selection_options_widget,
                "lasso": self.selection_options_widget,
                "shapes": getattr(self, "shapes_options_widget", self.brush_props_widget),
                "shape_rect": getattr(self, "shapes_options_widget", self.brush_props_widget),
                "shape_ellipse": getattr(self, "shapes_options_widget", self.brush_props_widget),
                "shape_line": getattr(self, "shapes_options_widget", self.brush_props_widget),
                "shape_polygon": getattr(self, "shapes_options_widget", self.brush_props_widget),
                "shape_star": getattr(self, "shapes_options_widget", self.brush_props_widget),
            }
            target = tool_to_widget.get(tool_name, self.brush_props_widget)
            self.stacked_tool_props.setCurrentWidget(target)

    def _on_selection_options_changed(self, settings: dict) -> None:
        tool = getattr(self, "_active_tool_id", "rect_select")
        if tool not in ("rect_select", "ellipse_select", "lasso"):
            tool = "rect_select"
        self.toolOptionsChanged.emit(tool, settings)

    def _on_tool(self, tool_id: str) -> None:
        self.set_tool_active(tool_id)
        self.toolActivated.emit(tool_id)
        if tool_id == "shapes" and hasattr(self, "shapes_options_widget"):
            self.shapes_options_widget._emit_changes()

    def set_color(self, color: QtGui.QColor) -> None:
        if hasattr(self, "color_wheel") and self.color_wheel:
            self.color_wheel.set_color(color)
        if hasattr(self, "stroke_preview") and self.stroke_preview:
            self.stroke_preview.update_brush_state(color=[color.redF(), color.greenF(), color.blueF()])
        if hasattr(self, "eyedrop_options_widget"):
            self.eyedrop_options_widget.set_captured_color(color)
        if hasattr(self, "shapes_options_widget"):
            self.shapes_options_widget.set_active_color(color)

    def _on_size_changed(self, val: float) -> None:
        self.sizeChanged.emit(val)
        if self._adv_panel and hasattr(self._adv_panel, "slider_size"):
            self._adv_panel.slider_size.blockSignals(True)
            self._adv_panel.slider_size.setValue(int(val))
            self._adv_panel.slider_size.blockSignals(False)
        if hasattr(self, "stroke_preview"):
            self.stroke_preview.update_brush_state(size=val)

    def _on_opacity_changed(self, val: float) -> None:
        self.opacityChanged.emit(val)
        if self._adv_panel and hasattr(self._adv_panel, "slider_opacity"):
            self._adv_panel.slider_opacity.blockSignals(True)
            self._adv_panel.slider_opacity.setValue(int(val * 100))
            self._adv_panel.slider_opacity.blockSignals(False)
        if hasattr(self, "stroke_preview"):
            self.stroke_preview.update_brush_state(opacity=val)

    def _on_stabilizer_changed(self, val: float) -> None:
        self.stabilizerWeightChanged.emit(val)
        if self._adv_panel and hasattr(self._adv_panel, "slider_stabilizer"):
            self._adv_panel.slider_stabilizer.blockSignals(True)
            self._adv_panel.slider_stabilizer.setValue(int(val * 100))
            self._adv_panel.slider_stabilizer.blockSignals(False)

    def _on_spacing_changed(self, val: float) -> None:
        self.spacingChanged.emit(val)
        if self._adv_panel and hasattr(self._adv_panel, "slider_spacing"):
            self._adv_panel.slider_spacing.blockSignals(True)
            self._adv_panel.slider_spacing.setValue(int(val * 100))
            self._adv_panel.slider_spacing.blockSignals(False)
        if hasattr(self, "stroke_preview"):
            self.stroke_preview.update_brush_state(spacing=val)

    def _on_contrast_changed(self, val: float) -> None:
        self.contrastChanged.emit(val)
        if self._adv_panel and hasattr(self._adv_panel, "slider_contrast"):
            self._adv_panel.slider_contrast.blockSignals(True)
            self._adv_panel.slider_contrast.setValue(int(val * 100))
            self._adv_panel.slider_contrast.blockSignals(False)

    def _on_preset_changed(self, name: str, data: dict) -> None:
        self.sliders_section.sync_from_preset(data)
        if "brush_size" in data:
            self.sizeChanged.emit(float(data["brush_size"]))
        if "opacity" in data:
            self.opacityChanged.emit(float(data["opacity"]))
        if "stabilizer_weight" in data or "stabilizer" in data:
            sw = float(data.get("stabilizer_weight", data.get("stabilizer", 0.35)))
            self.stabilizerWeightChanged.emit(sw)
        if "spacing_factor" in data:
            self.spacingChanged.emit(float(data["spacing_factor"]))
        if "brush_grain_contrast" in data:
            self.contrastChanged.emit(float(data["brush_grain_contrast"]))
        elif "hardness" in data:
            self.contrastChanged.emit(float(data["hardness"]))

        if self._adv_panel:
            self._adv_panel.sync_from_engine_profile()

        if hasattr(self, "stroke_preview"):
            eng_type = data.get("engine_type", 0)
            sz = data.get("brush_size", self.size_slider.value())
            op = data.get("opacity", self.opacity_slider.value() / 100.0)
            hd = data.get("hardness", 0.85)
            sp = data.get("spacing_factor", 0.10)
            self.stroke_preview.update_brush_state(
                size=sz, opacity=op, hardness=hd, spacing=sp, engine_type=eng_type
            )

    def _open_advanced_dialog(self) -> None:
        if self._adv_panel is None:
            self._adv_panel = AdvancedPanel(self)
            self._adv_panel.sizeChanged.connect(self._sync_size_from_adv)
            self._adv_panel.opacityChanged.connect(self._sync_opacity_from_adv)
            self._adv_panel.stabilizerWeightChanged.connect(self._sync_stabilizer_from_adv)
            self._adv_panel.spacingChanged.connect(self._sync_spacing_from_adv)
            self._adv_panel.contrastChanged.connect(self._sync_contrast_from_adv)

            self._adv_panel.pressureChanged.connect(self.pressureChanged.emit)
            self._adv_panel.pressureCurvePowerChanged.connect(self.pressureCurvePowerChanged.emit)
            self._adv_panel.minDensityActiveChanged.connect(self.minDensityActiveChanged.emit)
            self._adv_panel.minDensityValueChanged.connect(self.minDensityValueChanged.emit)
            self._adv_panel.invertHeightChanged.connect(self.invertHeightChanged.emit)
            self._adv_panel.loadShapeRequested.connect(self.loadShapeRequested.emit)
            self._adv_panel.loadHeightmapRequested.connect(self.loadHeightmapRequested.emit)
            self._adv_panel.pinToggled.connect(self._on_pin_toggled)

        if self._adv_panel.isVisible():
            self._adv_panel.hide()
        else:
            self._adv_panel.sync_from_engine_profile()
            self._adv_panel.show_near(self.btn_adv)

    def _sync_size_from_adv(self, val: float) -> None:
        self.sliders_section.sync_size(val)
        self.sizeChanged.emit(val)
        if hasattr(self, "stroke_preview"):
            self.stroke_preview.update_preview()

    def _sync_opacity_from_adv(self, val: float) -> None:
        self.sliders_section.sync_opacity(val)
        self.opacityChanged.emit(val)
        if hasattr(self, "stroke_preview"):
            self.stroke_preview.update_preview()

    def _sync_stabilizer_from_adv(self, val: float) -> None:
        self.sliders_section.sync_stabilizer(val)
        self.stabilizerWeightChanged.emit(val)

    def _sync_spacing_from_adv(self, val: float) -> None:
        self.sliders_section.sync_spacing(val)
        self.spacingChanged.emit(val)

    def _sync_contrast_from_adv(self, val: float) -> None:
        self.sliders_section.sync_contrast(val)
        self.contrastChanged.emit(val)

    def _on_pin_toggled(self, param_name: str, is_pinned: bool) -> None:
        self.sliders_section.set_pinned_visible(param_name, is_pinned)
