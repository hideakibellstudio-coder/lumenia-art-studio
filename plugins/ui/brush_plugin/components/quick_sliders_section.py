"""QuickSlidersSection — Slider controls and pinned parameters for BrushSettingsPanel.

Decoupled under ARCcC v2 (< 180 LOC).
"""

from __future__ import annotations

from typing import Dict, List
from PySide6 import QtCore, QtWidgets

from ..compact_slider import CompactSlider
from ui.core.theme.manager import ThemeManager
from ui.core.i18n import tr

class QuickSlidersSection(QtWidgets.QWidget):
    """Section widget containing basic and pinnable parameter sliders."""

    sizeChanged               = QtCore.Signal(float)
    opacityChanged            = QtCore.Signal(float)
    contrastChanged           = QtCore.Signal(float)
    pressureChanged           = QtCore.Signal(float)
    pressureCurvePowerChanged = QtCore.Signal(float)
    stabilizerWeightChanged   = QtCore.Signal(float)
    spacingChanged            = QtCore.Signal(float)
    minDensityValueChanged    = QtCore.Signal(float)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("QuickSlidersSection")

        self.lbl_quick = QtWidgets.QLabel("PARÂMETROS RÁPIDOS", self)
        self.lbl_quick.setObjectName("BSectionLabel")

        self.size_slider = CompactSlider("Tam:", 1, 500, "px", self)
        self.size_slider.setValue(60)
        self.size_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.opacity_slider = CompactSlider("Opac:", 0, 100, "%", self)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.contrast_slider = CompactSlider("Dur:", 1, 30, "", self)
        self.contrast_slider.setValue(10)
        self.contrast_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.contrast_slider.setVisible(False)

        self.pressure_slider = CompactSlider("Press:", 1, 100, "%", self)
        self.pressure_slider.setValue(50)
        self.pressure_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.pressure_slider.setVisible(False)

        self.curve_slider = CompactSlider("Curv:", 1, 40, "", self)
        self.curve_slider.setValue(10)
        self.curve_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.curve_slider.setVisible(False)

        self.stabilizer_slider = CompactSlider("Stab:", 0, 98, "%", self)
        self.stabilizer_slider.setValue(35)
        self.stabilizer_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.stabilizer_slider.setVisible(False)

        self.spacing_slider = CompactSlider("Espac:", 1, 100, "%", self)
        self.spacing_slider.setValue(10)
        self.spacing_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.spacing_slider.setVisible(False)

        self.min_density_slider = CompactSlider("Dens:", 0, 100, "%", self)
        self.min_density_slider.setValue(0)
        self.min_density_slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.min_density_slider.setVisible(False)

        self._slider_map: Dict[str, CompactSlider] = {
            "size": self.size_slider,
            "opacity": self.opacity_slider,
            "contrast": self.contrast_slider,
            "pressure": self.pressure_slider,
            "pressure_curve": self.curve_slider,
            "stabilizer": self.stabilizer_slider,
            "spacing": self.spacing_slider,
            "min_density": self.min_density_slider,
        }

        self._build_layout()
        self._connect_signals()

    def _build_layout(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(self.lbl_quick)
        layout.addWidget(self.size_slider)
        layout.addWidget(self.opacity_slider)
        layout.addWidget(self.contrast_slider)
        layout.addWidget(self.pressure_slider)
        layout.addWidget(self.curve_slider)
        layout.addWidget(self.stabilizer_slider)
        layout.addWidget(self.spacing_slider)
        layout.addWidget(self.min_density_slider)
        layout.addStretch()

    def _connect_signals(self) -> None:
        self.size_slider.valueChanged.connect(lambda v: self.sizeChanged.emit(float(v)))
        self.opacity_slider.valueChanged.connect(lambda v: self.opacityChanged.emit(v / 100.0))
        self.contrast_slider.valueChanged.connect(lambda v: self.contrastChanged.emit(v / 10.0))
        self.pressure_slider.valueChanged.connect(lambda v: self.pressureChanged.emit(v / 100.0))
        self.curve_slider.valueChanged.connect(lambda v: self.pressureCurvePowerChanged.emit(v / 10.0))
        self.stabilizer_slider.valueChanged.connect(lambda v: self.stabilizerWeightChanged.emit(v / 100.0))
        self.spacing_slider.valueChanged.connect(lambda v: self.spacingChanged.emit(v / 100.0))
        self.min_density_slider.valueChanged.connect(lambda v: self.minDensityValueChanged.emit(v / 100.0))

    @property
    def all_sliders(self) -> List[CompactSlider]:
        return list(self._slider_map.values())

    def set_pinned_visible(self, param_name: str, is_pinned: bool) -> None:
        if param_name in self._slider_map:
            self._slider_map[param_name].setVisible(is_pinned)

    def sync_size(self, val: float) -> None:
        self.size_slider.blockSignals(True)
        self.size_slider.setValue(int(val))
        self.size_slider.blockSignals(False)

    def sync_opacity(self, val: float) -> None:
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(int(val * 100))
        self.opacity_slider.blockSignals(False)

    def sync_stabilizer(self, val: float) -> None:
        self.stabilizer_slider.blockSignals(True)
        self.stabilizer_slider.setValue(int(round(val * 100)))
        self.stabilizer_slider.blockSignals(False)

    def sync_spacing(self, val: float) -> None:
        self.spacing_slider.blockSignals(True)
        self.spacing_slider.setValue(int(round(val * 100)))
        self.spacing_slider.blockSignals(False)

    def sync_contrast(self, val: float) -> None:
        self.contrast_slider.blockSignals(True)
        self.contrast_slider.setValue(int(round(val * 10)))
        self.contrast_slider.blockSignals(False)

    def sync_from_preset(self, data: dict) -> None:
        if "brush_size" in data:
            self.sync_size(float(data["brush_size"]))
        if "opacity" in data:
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(int(data["opacity"] * 100))
            self.opacity_slider.blockSignals(False)
        if "stabilizer_weight" in data or "stabilizer" in data:
            sw = float(data.get("stabilizer_weight", data.get("stabilizer", 0.35)))
            self.sync_stabilizer(sw)
        if "spacing_factor" in data:
            self.sync_spacing(float(data["spacing_factor"]))
        if "brush_grain_contrast" in data:
            self.sync_contrast(float(data["brush_grain_contrast"]))
        elif "hardness" in data:
            self.sync_contrast(float(data["hardness"]))

    def retranslate_ui(self) -> None:
        self.lbl_quick.setText(tr("brush.quick_params", "PARÂMETROS RÁPIDOS"))
        self.size_slider.setPrefix(tr("brush.size_short", "Tam:"))
        self.opacity_slider.setPrefix(tr("brush.opacity_short", "Opac:"))
        self.contrast_slider.setPrefix(tr("brush.hardness_short", "Dur:"))
        self.pressure_slider.setPrefix(tr("brush.pressure_short", "Press:"))
        self.curve_slider.setPrefix(tr("brush.curve_short", "Curv:"))
        self.stabilizer_slider.setPrefix(tr("brush.stabilizer_short", "Stab:"))
        self.spacing_slider.setPrefix(tr("brush.spacing_short", "Espac:"))
        self.min_density_slider.setPrefix(tr("brush.density_short", "Dens:"))

    def apply_theme_style(self, theme: ThemeManager) -> None:
        text_sec = theme.get_color("text_sec")
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
