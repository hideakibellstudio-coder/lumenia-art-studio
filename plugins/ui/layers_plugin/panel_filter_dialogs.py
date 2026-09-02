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
from ui.core.i18n import tr


class FilterLayerDialog(BaseFramelessDialog):
    """Diálogo de seleção do tipo de filtro de camada."""

    FILTERS = [
        ("brightness", "filter.brightness_contrast", "Brilho / Contraste"),
        ("huesat",     "filter.hue_saturation", "Matiz / Saturação / Luminosidade"),
        ("pixelate",   "filter.pixelate", "Pixelizar"),
        ("invert",     "filter.invert", "Inverter Cores"),
        ("sharpen",    "filter.sharpen", "Nitidez (Sharpen)"),
        ("vignette",   "filter.vignette", "Vinheta"),
    ]

    def __init__(self, parent=None):
        super().__init__(title=tr("layers.add_filter", "Adicionar Camada de Filtro"), icon_name="filter", parent=parent, modal=True)
        self.resize(360, 320)

        title = QLabel(f"<b>{tr('filter.choose_type', 'Escolha o tipo de efeito:')}</b>")
        self.content_layout.addWidget(title)

        self._btn_group = QButtonGroup(self)
        self._type_keys = []

        for i, (key, i18n_key, dflt_label) in enumerate(self.FILTERS):
            rb = QRadioButton(tr(i18n_key, dflt_label))
            if i == 0:
                rb.setChecked(True)
            self._btn_group.addButton(rb, i)
            self._type_keys.append(key)
            self.content_layout.addWidget(rb)

        self.content_layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton(tr("dialogs.cancel", "Cancelar"))
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_ok = QPushButton(tr("dialogs.ok", "OK"))
        btn_ok.setObjectName("accentButton")
        btn_ok.setDefault(True)
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
            ("filter.brightness", "Brilho",    0, -100, 100, 0,   100.0),
            ("filter.contrast",   "Contraste", 1, -100, 100, 0,   100.0),
        ],
        "huesat": [
            ("filter.hue",        "Matiz",      0, -180, 180,  0, 1.0),
            ("filter.saturation", "Saturação",  1, -100, 100,  0, 100.0),
            ("filter.lightness",  "Luminosidade",2, -100, 100, 0, 100.0),
        ],
        "pixelate": [
            ("filter.block_size", "Tamanho do Bloco", 0, 2, 128, 8, 1.0),
        ],
        "invert": [],
        "sharpen": [
            ("filter.intensity",  "Intensidade", 0, 0, 200, 50, 100.0),
        ],
        "vignette": [
            ("filter.radius",     "Raio",       0, 0, 100, 70, 100.0),
            ("filter.feather",    "Suavidade",  1, 0, 100, 50, 100.0),
            ("filter.intensity",  "Intensidade",2, 0, 100, 80, 100.0),
        ],
    }

    LABELS = {
        "brightness": ("filter.brightness_contrast", "Brilho / Contraste"),
        "huesat":     ("filter.hue_saturation", "Matiz / Saturação"),
        "pixelate":   ("filter.pixelate", "Pixelizar"),
        "invert":     ("filter.invert", "Inverter Cores"),
        "sharpen":    ("filter.sharpen", "Nitidez"),
        "vignette":   ("filter.vignette", "Vinheta"),
    }

    def __init__(self, parent, layer_id: int, filter_type: str):
        i18n_info = self.LABELS.get(filter_type, ("filter.adjustments", "Filtro"))
        label = tr(i18n_info[0], i18n_info[1])
        super().__init__(title=f"{tr('filter.adjustment_title', 'Ajuste de Filtro')} — {label}", icon_name="filter", parent=parent, modal=True)
        self.resize(380, 280)
        self.layer_id = layer_id
        self.filter_type = filter_type
        self._params = [0.0] * 8

        param_defs = self.PARAMS.get(filter_type, [])

        if not param_defs:
            self.content_layout.addWidget(QLabel(tr("filter.no_additional_params", "Este filtro não tem parâmetros adicionais.\nUse o slider de Opacidade da camada para controlar a intensidade.")))
        else:
            group = QGroupBox(tr("brush.params", "Parâmetros"))
            glayout = QVBoxLayout(group)
            glayout.setSpacing(6)

            for (i18n_key, dflt_lbl, slot, mn, mx, dflt, scale) in param_defs:
                row = QHBoxLayout()
                row.addWidget(QLabel(tr(i18n_key, dflt_lbl)))

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
                    sl.valueChanged.connect(on_change)
                    self._params[s] = dflt / sc
                make_handler(slot, slider, val_lbl, scale)

            self.content_layout.addWidget(group)

        self.content_layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_ok = QPushButton(tr("dialogs.ok", "OK"))
        btn_ok.setObjectName("accentButton")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)

        self.content_layout.addLayout(btn_box)

    def get_parameters(self) -> list[float]:
        return self._params
