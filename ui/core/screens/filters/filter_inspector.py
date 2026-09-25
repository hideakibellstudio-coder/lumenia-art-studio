"""
filter_inspector.py — Painel Inspetor Dinâmico de Parâmetros de Filtros.
========================================================================
Gera dinamicamente controles (sliders com botões -/+, checkboxes de alternância)
baseado no esquema de parâmetros do filtro selecionado, emitindo alterações reativas.
100% conforme ARCcC e integrado ao ThemeManager.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.widgets.slider.labeled_slider import LabeledSlider
from ui.infrastructure.theme.manager import ThemeManager


class FilterInspector(QtWidgets.QWidget):
    """Painel lateral direito que exibe e edita os parâmetros de um filtro ativo."""

    params_changed = QtCore.Signal(list)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._active_def: Optional[dict] = None
        self._param_widgets: Dict[str, Any] = {}

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self.update_style)
        self.update_style()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.title_lbl = QtWidgets.QLabel("PARÂMETROS DO FILTRO")
        self.title_lbl.setProperty("heading", "true")
        layout.addWidget(self.title_lbl)

        self.desc_lbl = QtWidgets.QLabel("Ajuste os parâmetros abaixo para criar a camada.")
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setProperty("muted", "true")
        layout.addWidget(self.desc_lbl)

        # Container dos sliders dinâmicos
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.inner = QtWidgets.QWidget()
        self.params_layout = QtWidgets.QVBoxLayout(self.inner)
        self.params_layout.setContentsMargins(0, 4, 0, 4)
        self.params_layout.setSpacing(12)
        self.params_layout.setAlignment(QtCore.Qt.AlignTop)

        self.scroll.setWidget(self.inner)
        layout.addWidget(self.scroll, 1)

    def set_filter_def(self, fdef: dict, initial_params: Optional[list[float]] = None) -> None:
        self._active_def = fdef
        self.title_lbl.setText(fdef["name"].upper())
        self.desc_lbl.setText(fdef["description"])

        # Limpa widgets anteriores
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._param_widgets.clear()

        for idx, p in enumerate(fdef["params"]):
            init_val = None
            if initial_params and idx < len(initial_params):
                init_val = initial_params[idx]

            if p.get("type") == "bool":
                chk = QtWidgets.QCheckBox(p["label"])
                val = bool(init_val) if init_val is not None else bool(p["default"])
                chk.setChecked(val)
                chk.toggled.connect(lambda *_: self._on_param_changed())
                self.params_layout.addWidget(chk)
                self._param_widgets[p["id"]] = chk
            else:
                factor = p.get("factor", 1.0)
                sld = LabeledSlider(
                    label_text=p["label"],
                    min_val=p["min"],
                    max_val=p["max"],
                    default_val=p["default"],
                    value_suffix=p.get("suffix", ""),
                    divisor=factor
                )
                if init_val is not None:
                    sld.setValue(init_val)
                sld.valueChanged.connect(lambda *_: self._on_param_changed())
                self.params_layout.addWidget(sld)
                self._param_widgets[p["id"]] = sld

        self.update_style()
        self._on_param_changed()

    def get_param_values(self) -> list[float]:
        values: list[float] = []
        if not self._active_def:
            return values

        for p in self._active_def["params"]:
            w = self._param_widgets.get(p["id"])
            if w is None:
                continue

            if p.get("type") == "bool":
                values.append(1.0 if w.isChecked() else 0.0)
            else:
                factor = p.get("factor", 1.0)
                values.append(float(w.value()) / factor)

        return values

    def _on_param_changed(self) -> None:
        vals = self.get_param_values()
        self.params_changed.emit(vals)

    def update_style(self) -> None:
        tm = ThemeManager.instance()
        text_main = tm.get_color("text_main")
        text_muted = tm.get_color("text_muted")
        accent = tm.get_color("accent")

        self.title_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {accent};")
        self.desc_lbl.setStyleSheet(f"font-size: 11px; color: {text_muted};")
