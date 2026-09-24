"""AdvancedSection — base das seções do painel avançado do pincel.

Cada seção é dona dos próprios widgets e sabe mostrar e editar três tipos de
controle:

- rápido (`quick_slider`/`quick_check`): parâmetro do `BrushState`; editar
  chama `brush.set_value`, e `show_param` mostra o valor do estado;
- do motor (`engine_slider`/`engine_check`/`engine_combo`): editar escreve no
  motor pelo `BrushEngineWriter`; `show_profile` mostra o perfil do motor.

Até 2026-09-24 as seções eram funções `create_*_section(panel)` que
penduravam os widgets no painel, e o painel relia cada um com `hasattr`.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtCore, QtWidgets

from ui.core.state import BrushParam, BrushState
from ui.core.widgets.collapsible_section import CollapsibleSection
from ui.core.widgets.slider import LabeledSlider

from ..brush_engine_writer import BrushEngineWriter
from ..non_scroll_combo_box import NonScrollComboBox


class AdvancedSection(CollapsibleSection):
    # (nome do pin, fixado?) -> o painel principal mostra/esconde o slider rápido.
    pinToggled = QtCore.Signal(str, bool)

    def __init__(self, title: str, brush: BrushState, writer: BrushEngineWriter) -> None:
        super().__init__(title, expanded=True)
        self._brush = brush
        self._writer = writer
        # widget, chave do perfil, fator motor->widget, padrão
        self._profile_sliders: list[tuple[LabeledSlider, str, float, float]] = []
        self._profile_checks: list[tuple[QtWidgets.QCheckBox, str, bool]] = []
        self._profile_combos: list[tuple[QtWidgets.QComboBox, str]] = []
        self._quick: dict[BrushParam, tuple[QtWidgets.QWidget, float]] = {}
        body = QtWidgets.QWidget()
        self.body = QtWidgets.QVBoxLayout(body)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(6)
        self.add_widget(body)

    # ── Construção ────────────────────────────────────────────────────────

    def quick_slider(self, param: BrushParam, label: str, lo: int, hi: int, default: int, unit: str,
                     scale: float, pin: str, pinned: bool) -> LabeledSlider:
        slider = LabeledSlider(f"{label}:", lo, hi, default, unit, param_name=pin, show_pin=True,
                               default_pinned=pinned)
        slider.valueChanged.connect(lambda v: self._brush.set_value(param, v / scale))
        slider.pinToggled.connect(self.pinToggled)
        self._quick[param] = (slider, scale)
        self.body.addWidget(slider)
        return slider

    def quick_check(self, param: BrushParam, label: str) -> QtWidgets.QCheckBox:
        check = QtWidgets.QCheckBox(label)
        check.toggled.connect(lambda checked: self._brush.set_value(param, bool(checked)))
        self._quick[param] = (check, 1.0)
        self.body.addWidget(check)
        return check

    def engine_slider(self, label: str, lo: int, hi: int, default: int, unit: str,
                      profile_key: str, scale: float, write: Callable[[float], None],
                      profile_default: float = 0.0) -> LabeledSlider:
        slider = LabeledSlider(f"{label}:", lo, hi, default, unit)
        slider.valueChanged.connect(lambda v: write(float(v / scale)))
        self._profile_sliders.append((slider, profile_key, scale, profile_default))
        self.body.addWidget(slider)
        return slider

    def engine_check(self, label: str, profile_key: str, write: Callable[[bool], None],
                     checked: bool = False) -> QtWidgets.QCheckBox:
        check = QtWidgets.QCheckBox(label)
        check.setChecked(checked)
        check.toggled.connect(lambda state: write(bool(state)))
        self._profile_checks.append((check, profile_key, checked))
        self.body.addWidget(check)
        return check

    def engine_combo(self, items: list[str], write: Callable[[int], None],
                     profile_key: Optional[str] = None) -> NonScrollComboBox:
        combo = NonScrollComboBox()
        combo.addItems(items)
        combo.currentIndexChanged.connect(write)
        if profile_key:
            self._profile_combos.append((combo, profile_key))
        return combo

    def preview_header(self, combo: QtWidgets.QComboBox, load_label: str,
                       on_load: Callable[[], None]) -> QtWidgets.QLabel:
        """Linha com miniatura 46×46, combo de presets e botão de carregar PNG."""
        row = QtWidgets.QHBoxLayout()
        preview = QtWidgets.QLabel()
        preview.setFixedSize(46, 46)
        preview.setObjectName("BTexPreview")
        preview.setAlignment(QtCore.Qt.AlignCenter)
        row.addWidget(preview)
        info = QtWidgets.QWidget()
        info_layout = QtWidgets.QVBoxLayout(info)
        info_layout.setContentsMargins(4, 0, 0, 0)
        info_layout.setSpacing(4)
        button = QtWidgets.QPushButton(load_label)
        button.setObjectName("BTexBtn")
        button.setFixedHeight(22)
        button.setCursor(QtCore.Qt.PointingHandCursor)
        button.clicked.connect(on_load)
        info_layout.addWidget(combo)
        info_layout.addWidget(button)
        row.addWidget(info, 1)
        self.body.addLayout(row)
        return preview

    # ── Estado → tela ─────────────────────────────────────────────────────

    def show_param(self, param: BrushParam, value) -> None:
        """Valor de um parâmetro rápido do BrushState."""
        spec = self._quick.get(param)
        if spec is None:
            return
        widget, scale = spec
        widget.blockSignals(True)
        if isinstance(widget, QtWidgets.QCheckBox):
            widget.setChecked(bool(value))
        else:
            widget.setValue(int(round(float(value) * scale)))
        widget.blockSignals(False)

    def show_profile(self, profile: dict) -> None:
        """Parâmetros avançados lidos do perfil do motor."""
        for slider, key, scale, default in self._profile_sliders:
            slider.blockSignals(True)
            slider.setValue(int(profile.get(key, default) * scale))
            slider.blockSignals(False)
        for check, key, default in self._profile_checks:
            check.blockSignals(True)
            check.setChecked(bool(profile.get(key, default)))
            check.blockSignals(False)
        for combo, key in self._profile_combos:
            combo.blockSignals(True)
            combo.setCurrentIndex(min(int(profile.get(key, 0)), combo.count() - 1))
            combo.blockSignals(False)
        self.refresh_preview()

    def refresh_preview(self) -> None:
        """Seções com miniatura do motor sobrescrevem."""
