"""Section 3: Brush Jitters and Random Variations."""

from PySide6 import QtWidgets
from ui.core.widgets.slider import LabeledSlider
from ..collapsible_section import CollapsibleSection

def create_jitters_section(panel) -> CollapsibleSection:
    sec = CollapsibleSection("3. Jitters (Variações Aleatórias)", expanded=True)
    w = QtWidgets.QWidget()
    lo = QtWidgets.QVBoxLayout(w)
    lo.setContentsMargins(0, 0, 0, 0)
    lo.setSpacing(6)

    panel.sl_jit_size = LabeledSlider("Jitter de Tamanho:", 0, 100, 0, "%")
    panel.sl_jit_size.valueChanged.connect(panel._on_jit_size)
    lo.addWidget(panel.sl_jit_size)

    panel.sl_jit_angle = LabeledSlider("Jitter de Rotação:", 0, 100, 0, "%")
    panel.sl_jit_angle.valueChanged.connect(panel._on_jit_angle)
    lo.addWidget(panel.sl_jit_angle)

    panel.sl_jit_pos = LabeledSlider("Jitter de Posição (Deslocamento):", 0, 100, 0, "%")
    panel.sl_jit_pos.valueChanged.connect(panel._on_jit_pos)
    lo.addWidget(panel.sl_jit_pos)

    sec.add_widget(w)
    return sec
