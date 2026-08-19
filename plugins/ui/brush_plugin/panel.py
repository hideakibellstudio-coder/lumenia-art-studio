"""
BrushSettingsPanel — Painel Isolado de Configurações de Pincéis & Ferramentas
=============================================================================
Painel individual contendo os controles de seleção de presets (QComboBox),
botão de engrenagem (⚙), preview do traço e parâmetros rápidos, envolvido na moldura padronizada PanelCardBox
com suporte 100% dinâmico a temas (claro/escuro).
"""

from __future__ import annotations

import math
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.icons import get_icon

from .stroke_preview import StrokePreview
from .compact_slider import CompactSlider
from .advanced_panel import AdvancedPanel

from ui.core.widgets.card_box import PanelCardBox
from ui.core.theme.manager import ThemeManager
from .brush_dropdown import BrushDropdown
from ui.core.tools import TOOL_META


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
    toolActivated             = QtCore.Signal(str) # ID da ferramenta selecionada

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BrushSettingsPanel")

        self._adv_panel = None
        self._quick_sliders = []
        self._tool_buttons = {}

        self.setup_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme_style)
        self._apply_theme_style()

    @property
    def qs_size(self):
        return self.size_slider

    @property
    def qs_opacity(self):
        return self.opacity_slider


    def setup_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(0)

        # Content Widget
        content_widget = QtWidgets.QWidget()
        settings_layout = QtWidgets.QHBoxLayout(content_widget)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(4)

        # Tool Grid Column (Coluna Vertical Única com 10 Ferramentas)
        settings_layout.addWidget(self._make_tool_column())

        # Vertical Divider
        self.vline = QtWidgets.QFrame()
        self.vline.setFrameShape(QtWidgets.QFrame.VLine)
        self.vline.setObjectName("DockVLine")
        settings_layout.addWidget(self.vline)

        from ui.core.widgets.tool_options_widgets import (
            EyedropOptionsWidget, BucketOptionsWidget, WandOptionsWidget,
            TransformOptionsWidget, SelectionOptionsWidget
        )

        # Quick Sliders & Preview Column (Stacked por Ferramenta)
        props_col = QtWidgets.QWidget()
        props_col.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        col_layout = QtWidgets.QVBoxLayout(props_col)
        col_layout.setContentsMargins(0, 0, 0, 0)
        col_layout.setSpacing(0)

        self.stacked_tool_props = QtWidgets.QStackedWidget(props_col)

        # ── 1. Página de Pincéis & Parâmetros Rápidos ────────────────────────
        self.brush_props_widget = QtWidgets.QWidget()
        props_layout = QtWidgets.QVBoxLayout(self.brush_props_widget)
        props_layout.setContentsMargins(0, 0, 0, 0)
        props_layout.setSpacing(5)

        # ── Linha Superior: BrushDropdown Estilo Legado + Botão Engrenagem (⚙) ──
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

        # Stroke Preview Widget
        self.stroke_preview = StrokePreview(self)
        self.stroke_preview.setFixedHeight(48)
        self.stroke_preview.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        props_layout.addWidget(self.stroke_preview)

        # Quick Sliders Section Label
        self.lbl_quick = QtWidgets.QLabel("PARÂMETROS RÁPIDOS")
        self.lbl_quick.setObjectName("BSectionLabel")
        props_layout.addWidget(self.lbl_quick)

        # Sliders: Tamanho (1..500) e Opacidade (0..100%)
        self.size_slider = CompactSlider("Tam:", 1, 500, "px", self)
        self.size_slider.setValue(60)
        self.size_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        props_layout.addWidget(self.size_slider)
        self._quick_sliders.append(self.size_slider)

        self.opacity_slider = CompactSlider("Opac:", 0, 100, "%", self)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        props_layout.addWidget(self.opacity_slider)
        self._quick_sliders.append(self.opacity_slider)

        # Sliders Pináveis Adicionais (Iniciam ocultos por padrão)
        self.contrast_slider = CompactSlider("Dur:", 1, 30, "", self)
        self.contrast_slider.setValue(10)
        self.contrast_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.contrast_slider.valueChanged.connect(lambda v: self.contrastChanged.emit(v / 10.0))
        self.contrast_slider.setVisible(False)
        props_layout.addWidget(self.contrast_slider)
        self._quick_sliders.append(self.contrast_slider)

        self.pressure_slider = CompactSlider("Press:", 1, 100, "%", self)
        self.pressure_slider.setValue(50)
        self.pressure_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.pressure_slider.valueChanged.connect(lambda v: self.pressureChanged.emit(v / 100.0))
        self.pressure_slider.setVisible(False)
        props_layout.addWidget(self.pressure_slider)
        self._quick_sliders.append(self.pressure_slider)

        self.curve_slider = CompactSlider("Curv:", 1, 40, "", self)
        self.curve_slider.setValue(10)
        self.curve_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.curve_slider.valueChanged.connect(lambda v: self.pressureCurvePowerChanged.emit(v / 10.0))
        self.curve_slider.setVisible(False)
        props_layout.addWidget(self.curve_slider)
        self._quick_sliders.append(self.curve_slider)

        self.stabilizer_slider = CompactSlider("Stab:", 0, 95, "%", self)
        self.stabilizer_slider.setValue(0)
        self.stabilizer_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.stabilizer_slider.valueChanged.connect(lambda v: self.stabilizerWeightChanged.emit(v / 100.0))
        self.stabilizer_slider.setVisible(False)
        props_layout.addWidget(self.stabilizer_slider)
        self._quick_sliders.append(self.stabilizer_slider)

        self.spacing_slider = CompactSlider("Espac:", 1, 100, "%", self)
        self.spacing_slider.setValue(10)
        self.spacing_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.spacing_slider.valueChanged.connect(lambda v: self.spacingChanged.emit(v / 100.0))
        self.spacing_slider.setVisible(False)
        props_layout.addWidget(self.spacing_slider)
        self._quick_sliders.append(self.spacing_slider)

        self.min_density_slider = CompactSlider("Dens:", 0, 100, "%", self)
        self.min_density_slider.setValue(0)
        self.min_density_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.min_density_slider.valueChanged.connect(lambda v: self.minDensityValueChanged.emit(v / 100.0))
        self.min_density_slider.setVisible(False)
        props_layout.addWidget(self.min_density_slider)
        self._quick_sliders.append(self.min_density_slider)

        props_layout.addStretch()
        self.stacked_tool_props.addWidget(self.brush_props_widget)

        # ── 2. Páginas de Opções de Ferramentas Específicas ─────────────────
        self.eyedrop_options_widget = EyedropOptionsWidget(self)
        self.stacked_tool_props.addWidget(self.eyedrop_options_widget)

        self.bucket_options_widget = BucketOptionsWidget(self)
        self.stacked_tool_props.addWidget(self.bucket_options_widget)

        self.wand_options_widget = WandOptionsWidget(self)
        self.stacked_tool_props.addWidget(self.wand_options_widget)

        self.transform_options_widget = TransformOptionsWidget(self)
        self.stacked_tool_props.addWidget(self.transform_options_widget)

        self.selection_options_widget = SelectionOptionsWidget(self)
        self.stacked_tool_props.addWidget(self.selection_options_widget)

        col_layout.addWidget(self.stacked_tool_props)
        settings_layout.addWidget(props_col, 1)

        # Card Box Wrapper
        card_box = PanelCardBox("🖌️ Pincel & Ferramentas", content_widget, self)

        # Scroll Area
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        scroll_content = QtWidgets.QWidget()
        sc_layout = QtWidgets.QVBoxLayout(scroll_content)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.addWidget(card_box)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _apply_theme_style(self, *args) -> None:
        theme = ThemeManager.instance()
        border = theme.get_color("border")
        text_sec = theme.get_color("text_sec")
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

        self.lbl_quick.setText("PARÂMETROS RÁPIDOS")
        self.lbl_quick.setStyleSheet(f"""
            QLabel {{
                color: {text_sec};
                font-size: 9px;
                font-weight: bold;
                margin-top: 2px;
                margin-bottom: 2px;
            }}
        """)

        self.vline.setStyleSheet(f"background-color: {border}; max-width: 1px;")

        col_box_style = f"""
            QFrame#ToolColBox {{
                background-color: rgba(0, 0, 0, 0.22);
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """
        if hasattr(self, "tool_col_box"):
            self.tool_col_box.setStyleSheet(col_box_style)

        bg_hover = theme.get_color("accent_muted")
        tool_style = f"""
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
            }}
            QToolButton:hover {{
                background-color: {bg_hover};
                border: 1px solid {border};
            }}
            QToolButton:checked {{
                background-color: {accent};
                border: 1px solid {border};
            }}
        """
        for tid, btn in self._tool_buttons.items():
            btn.setStyleSheet(tool_style)
            is_active = btn.isChecked()
            btn.setIcon(get_icon(TOOL_META[tid]["icon"], color="#ffffff" if is_active else "text_main"))

    def _make_tool_column(self) -> QtWidgets.QWidget:
        self.tool_col_box = QtWidgets.QFrame()
        self.tool_col_box.setObjectName("ToolColBox")
        self.tool_col_box.setFixedWidth(34)

        layout = QtWidgets.QVBoxLayout(self.tool_col_box)
        layout.setContentsMargins(2, 3, 2, 3)
        layout.setSpacing(2)
        layout.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

        self._tool_buttons = {}
        self._tool_bg = QtWidgets.QButtonGroup(self)
        self._tool_bg.setExclusive(True)

        for tid, meta in TOOL_META.items():
            btn = QtWidgets.QToolButton(self.tool_col_box)
            btn.setCheckable(True)
            btn.setFixedSize(28, 28)
            btn.setIconSize(QtCore.QSize(15, 15))
            btn.setToolTip(meta["name"])
            is_active = (tid == "brush")
            btn.setIcon(get_icon(meta["icon"], color="#ffffff" if is_active else "text_main"))
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, t=tid: self._on_tool(t))

            if tid == "brush":
                btn.setChecked(True)

            self._tool_bg.addButton(btn)
            self._tool_buttons[tid] = btn
            layout.addWidget(btn)

        layout.addStretch()
        return self.tool_col_box

    def set_tool_active(self, tool_name: str) -> None:
        """Sincroniza visualmente a ferramenta ativa no painel e no dropdown de presets sem reemitir sinal em loop."""
        for tid, btn in self._tool_buttons.items():
            btn.blockSignals(True)
            is_active = (tid == tool_name)
            btn.setChecked(is_active)
            btn.setIcon(get_icon(TOOL_META[tid]["icon"], color="#ffffff" if is_active else "text_main"))
            btn.blockSignals(False)

        if hasattr(self, "preset_combo") and self.preset_combo:
            self.preset_combo.sync_to_tool(tool_name)

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
            }
            target = tool_to_widget.get(tool_name, self.brush_props_widget)
            self.stacked_tool_props.setCurrentWidget(target)

    def _on_tool(self, tool_id: str) -> None:
        self.set_tool_active(tool_id)
        self.toolActivated.emit(tool_id)


    def set_color(self, color: QtGui.QColor) -> None:
        if hasattr(self, "color_wheel") and self.color_wheel:
            self.color_wheel.set_color(color)
        if hasattr(self, "stroke_preview") and self.stroke_preview:
            self.stroke_preview.update_brush_state(color=[color.redF(), color.greenF(), color.blueF()])
        if hasattr(self, "eyedrop_options_widget"):
            self.eyedrop_options_widget.set_captured_color(color)

    def _on_size_changed(self, val: float) -> None:
        self.sizeChanged.emit(val)
        if self._adv_panel and hasattr(self._adv_panel, "slider_size"):
            self._adv_panel.slider_size.blockSignals(True)
            self._adv_panel.slider_size.setValue(int(val))
            self._adv_panel.slider_size.blockSignals(False)
        if hasattr(self, "stroke_preview"):
            self.stroke_preview.update_brush_state(size=val)

    def _on_opacity_changed(self, val: float) -> None:
        self.opacityChanged.emit(val / 100.0)
        if self._adv_panel and hasattr(self._adv_panel, "slider_opacity"):
            self._adv_panel.slider_opacity.blockSignals(True)
            self._adv_panel.slider_opacity.setValue(int(val))
            self._adv_panel.slider_opacity.blockSignals(False)
        if hasattr(self, "stroke_preview"):
            self.stroke_preview.update_brush_state(opacity=val / 100.0)

    def _on_preset_changed(self, name: str, data: dict) -> None:
        if "brush_size" in data:
            self.size_slider.blockSignals(True)
            self.size_slider.setValue(int(data["brush_size"]))
            self.size_slider.blockSignals(False)
            self.sizeChanged.emit(float(data["brush_size"]))

        if "opacity" in data:
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(int(data["opacity"] * 100))
            self.opacity_slider.blockSignals(False)
            self.opacityChanged.emit(float(data["opacity"]))

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
        self.size_slider.blockSignals(True)
        self.size_slider.setValue(int(val))
        self.size_slider.blockSignals(False)
        self.sizeChanged.emit(val)
        if hasattr(self, "stroke_preview"):
            self.stroke_preview.update_preview()

    def _sync_opacity_from_adv(self, val: float) -> None:
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(int(val * 100))
        self.opacity_slider.blockSignals(False)
        self.opacityChanged.emit(val)
        if hasattr(self, "stroke_preview"):
            self.stroke_preview.update_preview()

    def _sync_stabilizer_from_adv(self, val: float) -> None:
        self.stabilizer_slider.blockSignals(True)
        self.stabilizer_slider.setValue(int(val * 100))
        self.stabilizer_slider.blockSignals(False)
        self.stabilizerWeightChanged.emit(val)

    def _sync_spacing_from_adv(self, val: float) -> None:
        self.spacing_slider.blockSignals(True)
        self.spacing_slider.setValue(int(val * 100))
        self.spacing_slider.blockSignals(False)
        self.spacingChanged.emit(val)

    def _sync_contrast_from_adv(self, val: float) -> None:
        self.contrast_slider.blockSignals(True)
        self.contrast_slider.setValue(int(val * 100))
        self.contrast_slider.blockSignals(False)
        self.contrastChanged.emit(val)

    def _on_pin_toggled(self, param_name: str, is_pinned: bool) -> None:
        slider_map = {
            "size": self.size_slider,
            "opacity": self.opacity_slider,
            "contrast": self.contrast_slider,
            "pressure": self.pressure_slider,
            "pressure_curve": self.curve_slider,
            "stabilizer": self.stabilizer_slider,
            "spacing": self.spacing_slider,
            "min_density": self.min_density_slider,
        }
        if param_name in slider_map:
            slider_map[param_name].setVisible(is_pinned)
