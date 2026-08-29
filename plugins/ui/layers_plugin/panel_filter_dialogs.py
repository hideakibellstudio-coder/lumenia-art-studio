"""
panel_filter_dialogs — Diálogos de Seleção e Configuração de Filtros de Camada
=============================================================================
Submódulo atômico do LayersPanel para exibição de diálogos auxiliares de filtro.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QVBoxLayout, QButtonGroup, QRadioButton,
    QGroupBox, QHBoxLayout, QSlider, QSizePolicy, QApplication, QPushButton
)
from ui.core.dialogs.base_dialog import BaseFramelessDialog


class FilterLayerDialog(BaseFramelessDialog):
    """Diálogo de seleção do tipo de filtro de camada."""

    FILTERS = [
        ("brightness", "Brilho / Contraste"),
        ("huesat",     "Matiz / Saturação / Luminosidade"),
        ("pixelate",   "Pixelizar"),
        ("invert",     "Inverter Cores"),
        ("sharpen",    "Nitidez (Sharpen)"),
        ("vignette",   "Vinheta"),
    ]

    def __init__(self, parent=None):
        super().__init__(title="Adicionar Camada de Filtro", icon_name="filter", parent=parent, modal=True)
        self.resize(360, 320)

        title = QLabel("<b>Escolha o tipo de efeito:</b>")
        self.content_layout.addWidget(title)

        self._btn_group = QButtonGroup(self)
        self._type_keys = []

        for i, (key, label) in enumerate(self.FILTERS):
            rb = QRadioButton(label)
            if i == 0:
                rb.setChecked(True)
            self._btn_group.addButton(rb, i)
            self._type_keys.append(key)
            self.content_layout.addWidget(rb)

        self.content_layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_ok = QPushButton("OK")
        btn_ok.setDefault(True)
        btn_ok.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)

        self.content_layout.addLayout(btn_box)

    def selected_filter_type(self) -> str:
        idx = self._btn_group.checkedId()
        return self._type_keys[idx] if 0 <= idx < len(self._type_keys) else "brightness"


class FilterParamsDialog(BaseFramelessDialog):
    """Diálogo de ajuste de parâmetros de filtro de camada."""

    PARAMS = {
        "brightness": [
            ("Brilho",    0, -100, 100, 0,   100.0),
            ("Contraste", 1, -100, 100, 0,   100.0),
        ],
        "huesat": [
            ("Matiz",      0, -180, 180,  0, 1.0),
            ("Saturação",  1, -100, 100,  0, 100.0),
            ("Luminosidade",2, -100, 100, 0, 100.0),
        ],
        "pixelate": [
            ("Tamanho do Bloco", 0, 2, 128, 8, 1.0),
        ],
        "invert": [],
        "sharpen": [
            ("Intensidade", 0, 0, 200, 50, 100.0),
        ],
        "vignette": [
            ("Raio",       0, 0, 100, 70, 100.0),
            ("Suavidade",  1, 0, 100, 50, 100.0),
            ("Intensidade",2, 0, 100, 80, 100.0),
        ],
    }

    LABELS = {
        "brightness": "Brilho / Contraste",
        "huesat":     "Matiz / Saturação",
        "pixelate":   "Pixelizar",
        "invert":     "Inverter Cores",
        "sharpen":    "Nitidez",
        "vignette":   "Vinheta",
    }

    def __init__(self, parent, layer_id: int, filter_type: str):
        label = self.LABELS.get(filter_type, "Filtro")
        super().__init__(title=f"Ajuste de Filtro — {label}", icon_name="filter", parent=parent, modal=True)
        self.resize(380, 280)
        self.layer_id = layer_id
        self.filter_type = filter_type
        self._params = [0.0] * 8

        param_defs = self.PARAMS.get(filter_type, [])

        if not param_defs:
            self.content_layout.addWidget(QLabel("Este filtro não tem parâmetros adicionais.\n"
                                                 "Use o slider de Opacidade da camada para controlar a intensidade."))
        else:
            group = QGroupBox("Parâmetros")
            glayout = QVBoxLayout(group)
            glayout.setSpacing(6)

            for (lbl, slot, mn, mx, dflt, scale) in param_defs:
                row = QHBoxLayout()
                row.addWidget(QLabel(lbl))

                slider = QSlider(Qt.Horizontal)
                slider.setRange(mn, mx)
                slider.setValue(dflt)
                slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

                val_lbl = QLabel(str(dflt))
                val_lbl.setFixedWidth(40)
                val_lbl.setAlignment(Qt.AlignRight | Qt.AlignBottom)

                row.addWidget(slider)
                row.addWidget(val_lbl)
                glayout.addLayout(row)

                def make_handler(s, sl, vl, sc):
                    def on_change(v):
                        real_val = v / sc
                        self._params[s] = real_val
                        vl.setText(f"{v:+d}" if sc == 1.0 else f"{real_val:+.2f}")
                        win = QApplication.activeWindow()
                        if win and hasattr(win, 'statusBar'):
                            win.statusBar().showMessage(f"Filtro: Parâmetro {s} ajustado para {real_val}.", 1000)
                    sl.valueChanged.connect(on_change)
                    self._params[s] = dflt / sc
                make_handler(slot, slider, val_lbl, scale)

            self.content_layout.addWidget(group)

        self.content_layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_ok = QPushButton("OK")
        btn_ok.setDefault(True)
        btn_ok.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)

        self.content_layout.addLayout(btn_box)
