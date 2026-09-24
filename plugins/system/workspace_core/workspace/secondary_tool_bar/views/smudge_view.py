"""Smudge: arrasto, coleta de cor e mistura (0–100% na tela, 0–1 no estado).

O motor recebe estes valores pelo `ToolEngineSync` (ui/core/state); a view só
edita o ToolState. O combo de presets é um atalho que preenche os três
valores de uma vez; o item mostrado é o preset que casa com os valores
atuais, então as duas orientações sempre concordam.
"""
from __future__ import annotations

from ui.core.state import ToolState

from .base import OrientedOptionsView, add_slider, combo, header_row, icon_label, set_value, slider, value_label

# (nome, arrasto, coleta, mistura) em %
_PRESETS = (
    ("Arrasto Suave", 80, 70, 50),
    ("Mistura de Tinta", 90, 85, 70),
    ("Esfuminho Pesado", 50, 50, 40),
)
_FIELDS = ("smudge_stretch", "color_pickup", "mix_ratio")


class SmudgeOptionsView(OrientedOptionsView):
    def __init__(self, tool_state: ToolState, orientation, parent=None):
        super().__init__(tool_state, "smudge", orientation, parent)

    def build(self, layout):
        v = self.vertical
        if v:
            layout.addLayout(header_row("smudge", "SMUDGE / MISTURA")[0])
        else:
            layout.addWidget(icon_label("smudge"))
        self.cbo_preset = combo([name for name, *_ in _PRESETS])
        layout.addWidget(self.cbo_preset)

        captions = (("Alongamento:", "Arrasto:"), ("Coleta de Cor:", "Coleta:"), ("Taxa de Mistura:", "Mix:"))
        self.sliders, self.value_labels = {}, {}
        for field, (long_caption, short_caption), low in zip(_FIELDS, captions, (1, 0, 0)):
            s = slider(low, 100, None if v else 50)
            lbl = value_label("")
            add_slider(self, long_caption if v else short_caption, s, lbl)
            s.valueChanged.connect(lambda x, f=field: self.publish(**{f: x / 100.0}))
            self.sliders[field], self.value_labels[field] = s, lbl

        self.cbo_preset.currentIndexChanged.connect(self._on_preset_chosen)

    def _on_preset_chosen(self, index: int) -> None:
        if 0 <= index < len(_PRESETS):
            _, *percents = _PRESETS[index]
            self.publish(**{f: p / 100.0 for f, p in zip(_FIELDS, percents)})

    def show_options(self, o):
        percents = [round(o[f] * 100) for f in _FIELDS]
        for field, pct in zip(_FIELDS, percents):
            set_value(self.sliders[field], pct)
            self.value_labels[field].setText(f"{pct}%")
        for index, (_, *preset) in enumerate(_PRESETS):
            if preset == percents:
                self.cbo_preset.setCurrentIndex(index)
                break
