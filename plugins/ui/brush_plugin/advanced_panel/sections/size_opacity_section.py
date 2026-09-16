"""Section 1: Brush Size, Opacity and Blending."""

from PySide6 import QtWidgets
from ui.core.widgets.slider import LabeledSlider
from ui.core.i18n import tr
from ..collapsible_section import CollapsibleSection
from ..non_scroll_combo_box import NonScrollComboBox

def create_size_opacity_section(panel) -> CollapsibleSection:
    sec = CollapsibleSection(tr("brush.sec_size_opacity", "1. Tamanho, Opacidade & Mesclagem"), expanded=True)
    w = QtWidgets.QWidget()
    lo = QtWidgets.QVBoxLayout(w)
    lo.setContentsMargins(0, 0, 0, 0)
    lo.setSpacing(6)

    panel.slider_size = LabeledSlider(f"{tr('brush.size', 'Tamanho')}:", 1, 500, 24, "px", param_name="size", show_pin=True, default_pinned=True)
    panel.slider_size.valueChanged.connect(panel.sizeChanged.emit)
    panel.slider_size.valueChanged.connect(panel._on_brush_size_changed)
    panel.slider_size.pinToggled.connect(panel.pinToggled.emit)
    lo.addWidget(panel.slider_size)

    panel.sl_min_size = LabeledSlider(f"{tr('brush.min_size', 'Tamanho Mínimo (Pressão)')}:", 0, 100, 0, "%")
    panel.sl_min_size.valueChanged.connect(panel._on_min_size)
    lo.addWidget(panel.sl_min_size)

    panel.slider_opacity = LabeledSlider(f"{tr('brush.opacity', 'Opacidade')}:", 1, 100, 100, "%", param_name="opacity", show_pin=True, default_pinned=True)
    panel.slider_opacity.valueChanged.connect(lambda v: panel.opacityChanged.emit(v / 100.0))
    panel.slider_opacity.valueChanged.connect(panel._on_brush_opacity_changed)
    panel.slider_opacity.pinToggled.connect(panel.pinToggled.emit)
    lo.addWidget(panel.slider_opacity)

    panel.sl_min_op = LabeledSlider(f"{tr('brush.min_opacity', 'Opacidade Mínima (Pressão)')}:", 0, 100, 0, "%")
    panel.sl_min_op.valueChanged.connect(panel._on_min_opacity)
    lo.addWidget(panel.sl_min_op)

    lo.addWidget(QtWidgets.QLabel(f"{tr('brush.blend_mode', 'Modo de Mesclagem')} (DabBlendMode):"))
    panel.cmb_blend = NonScrollComboBox()
    panel.cmb_blend.addItems([
        f"{tr('blend_mode.normal', 'Normal')} (Alpha Over)",
        f"{tr('blend_mode.multiply', 'Multiplicação')} (Marcador/Feltro)",
        f"{tr('blend_mode.additive', 'Aditivo')} (Luz / Glow)",
        f"{tr('blend_mode.erase', 'Borracha')} (Alpha Erase)"
    ])
    panel.cmb_blend.currentIndexChanged.connect(panel._on_blend_mode)
    lo.addWidget(panel.cmb_blend)

    panel.chk_vel_size = QtWidgets.QCheckBox(tr("brush.velocity_size", "Variação por Velocidade (Velocity Size)"))
    panel.chk_vel_size.stateChanged.connect(panel._on_vel_size)
    lo.addWidget(panel.chk_vel_size)

    panel.slider_stabilizer = LabeledSlider(f"{tr('brush.stabilizer_label', 'Suavização (Estabilizador)')}:", 0, 98, 40, "%", param_name="stabilizer", show_pin=True, default_pinned=False)
    panel.slider_stabilizer.valueChanged.connect(lambda v: panel.stabilizerWeightChanged.emit(v / 100.0))
    panel.slider_stabilizer.valueChanged.connect(panel._on_stabilizer_changed)
    panel.slider_stabilizer.pinToggled.connect(panel.pinToggled.emit)
    lo.addWidget(panel.slider_stabilizer)

    panel.chk_stroke_taper = QtWidgets.QCheckBox(tr("brush.stroke_taper", "Afunilamento na Soltura (Tapering no Pen Up)"))
    panel.chk_stroke_taper.setChecked(True)
    panel.chk_stroke_taper.stateChanged.connect(panel._on_stroke_taper_changed)
    lo.addWidget(panel.chk_stroke_taper)

    sec.add_widget(w)
    return sec
