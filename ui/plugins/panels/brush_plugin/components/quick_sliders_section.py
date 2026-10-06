"""QuickSlidersSection — sliders rápidos (e pináveis) do painel de pincel.

É uma view pura: não guarda valor nenhum além do que o slider mostra.
- o usuário mexe num slider → `paramEdited(BrushParam, valor)`;
- o estado mudou por outro caminho → quem é dono chama `show_value(...)`.

Conversão slider ↔ unidade do motor fica numa tabela só (`_SCALES`), usada nos
dois sentidos, para que ida e volta nunca discordem.
"""

from __future__ import annotations

from typing import Dict, List
from PySide6 import QtCore, QtWidgets

from ui.core.state import BrushParam
from ui.core.widgets.compact_slider import CompactSlider
from ui.infrastructure.theme.manager import ThemeManager
from ui.infrastructure.i18n import tr

# param -> (rótulo i18n, rótulo padrão, mínimo, máximo, sufixo, divisor slider→unidade, visível por padrão)
_SLIDERS: dict[BrushParam, tuple[str, str, int, int, str, float, bool]] = {
    BrushParam.SIZE: ("brush.size_short", "Tam:", 1, 500, "px", 1.0, True),
    BrushParam.OPACITY: ("brush.opacity_short", "Opac:", 0, 100, "%", 100.0, True),
    BrushParam.FLOW: ("brush.flow_short", "Fluxo:", 0, 100, "%", 100.0, True),
    BrushParam.CONTRAST: ("brush.hardness_short", "Dur:", 1, 30, "", 10.0, False),
    BrushParam.PRESSURE: ("brush.pressure_short", "Press:", 1, 100, "%", 100.0, False),
    BrushParam.PRESSURE_CURVE: ("brush.curve_short", "Curv:", 1, 40, "", 10.0, False),
    BrushParam.STABILIZER: ("brush.stabilizer_short", "Stab:", 0, 98, "%", 100.0, False),
    BrushParam.SPACING: ("brush.spacing_short", "Espac:", 1, 100, "%", 100.0, False),
    BrushParam.MIN_DENSITY_VALUE: ("brush.density_short", "Dens:", 0, 100, "%", 100.0, False),
}

# Nome usado pelo "pin" do painel avançado (LabeledSlider.param_name) -> parâmetro.
PIN_NAMES: dict[str, BrushParam] = {
    "size": BrushParam.SIZE,
    "opacity": BrushParam.OPACITY,
    "flow": BrushParam.FLOW,
    "contrast": BrushParam.CONTRAST,
    "pressure": BrushParam.PRESSURE,
    "pressure_curve": BrushParam.PRESSURE_CURVE,
    "stabilizer": BrushParam.STABILIZER,
    "spacing": BrushParam.SPACING,
    "min_density": BrushParam.MIN_DENSITY_VALUE,
}


class QuickSlidersSection(QtWidgets.QWidget):
    """Sliders básicos e pináveis do painel de pincel."""

    # (BrushParam, float) — já na unidade do motor.
    paramEdited = QtCore.Signal(object, float)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("QuickSlidersSection")

        self.lbl_quick = QtWidgets.QLabel(tr("brush.quick_params", "PARÂMETROS RÁPIDOS"), self)
        self.lbl_quick.setObjectName("BSectionLabel")

        self._sliders: Dict[BrushParam, CompactSlider] = {}
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(self.lbl_quick)
        for param, (_key, label, low, high, suffix, _div, visible) in _SLIDERS.items():
            slider = CompactSlider(label, low, high, suffix, self)
            slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            slider.setVisible(visible)
            slider.valueChanged.connect(lambda raw, p=param: self._on_slider(p, raw))
            layout.addWidget(slider)
            self._sliders[param] = slider
        layout.addStretch()

    # ── API da view ───────────────────────────────────────────────────────

    def slider(self, param: BrushParam) -> CompactSlider:
        return self._sliders[param]

    @property
    def all_sliders(self) -> List[CompactSlider]:
        return list(self._sliders.values())

    def show_value(self, param: BrushParam, value: float) -> None:
        """Mostra `value` (unidade do motor) sem emitir `paramEdited`."""
        slider = self._sliders.get(param)
        if slider is None:
            return
        raw = int(round(float(value) * _SLIDERS[param][5]))
        slider.blockSignals(True)
        slider.setValue(raw)
        slider.blockSignals(False)

    def set_pinned_visible(self, pin_name: str, is_pinned: bool) -> None:
        param = PIN_NAMES.get(pin_name)
        if param is not None:
            self._sliders[param].setVisible(is_pinned)

    def retranslate_ui(self) -> None:
        self.lbl_quick.setText(tr("brush.quick_params", "PARÂMETROS RÁPIDOS"))
        for param, (key, label, *_rest) in _SLIDERS.items():
            self._sliders[param].setPrefix(tr(key, label))

    def apply_theme_style(self, theme: ThemeManager) -> None:
        # Só estilo: o texto do rótulo pertence ao retranslate_ui (antes daqui
        # saía um setText fixo em português que desfazia a tradução a cada
        # troca de tema).
        text_sec = theme.get_color("text_sec")
        self.lbl_quick.setStyleSheet(f"""
            QLabel {{
                color: {text_sec};
                font-size: 9px;
                font-weight: bold;
                margin-top: 2px;
                margin-bottom: 2px;
            }}
        """)

    # ── Interno ───────────────────────────────────────────────────────────

    def _on_slider(self, param: BrushParam, raw: int) -> None:
        self.paramEdited.emit(param, raw / _SLIDERS[param][5])
