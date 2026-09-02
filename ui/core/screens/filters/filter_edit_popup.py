"""
FilterEditPopup — Popup/Inspector de Re-Edição de Parâmetros de Filtro
======================================================================
Permite que o usuário re-abra e re-ajuste os parâmetros de qualquer Camada de Ajuste
existente no grafo por duplo-clique ou botão direito no painel de camadas.
As alterações acionam a recomposição do canvas em tempo real.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.widgets.slider.labeled_slider import LabeledSlider
from .filter_adjustment_dialog import FILTER_DEFINITIONS


class FilterEditPopup(QtWidgets.QDialog):
    """
    Inspector flutuante para editar os parâmetros de uma camada de filtro já criada.
    """

    params_changed = QtCore.Signal(int, list)  # (layer_id, params_list)

    def __init__(self, layer_id: int, layer_name: str, filter_type_id: int, initial_params: List[float], parent=None):
        flags = QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint
        super().__init__(parent, flags)
        self.setWindowTitle(f"Editar Filtro: {layer_name}")
        self.setFixedWidth(360)

        self.layer_id = layer_id
        self.filter_type_id = filter_type_id
        self.current_params = list(initial_params) + [0.0] * 8
        self.current_params = self.current_params[:8]

        # Encontra a definição correspondente ao type_id
        self.fdef = next((f for f in FILTER_DEFINITIONS if f["type_id"] == filter_type_id), FILTER_DEFINITIONS[0])
        self._param_widgets: Dict[str, Any] = {}

        self._preview_timer = QtCore.QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(16)
        self._preview_timer.timeout.connect(self._do_emit_params_changed)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Header
        from ui.core.icons import get_icon
        header_box = QtWidgets.QHBoxLayout()
        header_icon = QtWidgets.QLabel()
        header_icon.setFixedSize(16, 16)
        header_icon.setPixmap(get_icon("settings").pixmap(16, 16))
        header_lbl = QtWidgets.QLabel(self.fdef['name'].upper())
        header_lbl.setProperty("heading", "true")
        header_box.addWidget(header_icon)
        header_box.addWidget(header_lbl)
        header_box.addStretch()
        layout.addLayout(header_box)

        desc_lbl = QtWidgets.QLabel(self.fdef["description"])
        desc_lbl.setWordWrap(True)
        desc_lbl.setProperty("muted", "true")
        layout.addWidget(desc_lbl)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(sep)

        # Dynamic Sliders / Checkboxes
        for idx, p in enumerate(self.fdef["params"]):
            init_val = self.current_params[idx] if idx < len(self.current_params) else p.get("default", 0)

            if p.get("type") == "bool":
                chk = QtWidgets.QCheckBox(p["label"])
                chk.setChecked(init_val > 0.5)
                chk.toggled.connect(self._on_param_changed)
                layout.addWidget(chk)
                self._param_widgets[p["id"]] = chk
            else:
                factor = p.get("factor", 1.0)
                int_init = int(init_val * factor) if factor != 1.0 else int(init_val)
                slider = LabeledSlider(
                    p["label"],
                    p["min"],
                    p["max"],
                    int_init,
                    value_suffix=p.get("suffix", "")
                )
                slider.valueChanged.connect(self._on_param_changed)
                layout.addWidget(slider)
                self._param_widgets[p["id"]] = slider

        layout.addStretch()

        # Botão Fechar
        btn_close = QtWidgets.QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _on_param_changed(self, *args) -> None:
        if not self._preview_timer.isActive():
            self._preview_timer.start()

    def _do_emit_params_changed(self) -> None:
        new_params = []
        for p in self.fdef["params"]:
            w = self._param_widgets.get(p["id"])
            if w:
                if isinstance(w, QtWidgets.QCheckBox):
                    val = 1.0 if w.isChecked() else 0.0
                elif isinstance(w, LabeledSlider):
                    raw_val = float(w.value())
                    factor = p.get("factor", 1.0)
                    val = raw_val / factor if factor != 1.0 else raw_val
                else:
                    val = 0.0
                new_params.append(val)
        while len(new_params) < 8:
            new_params.append(0.0)

        self.current_params = new_params
        self.params_changed.emit(self.layer_id, new_params)

    def _apply_theme(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        text_main = theme.get_color("text_main", "#f3f4f6")
        border = theme.get_color("border", "#2e2e38")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_panel};
                color: {text_main};
                border: 1px solid {border};
            }}
        """)
