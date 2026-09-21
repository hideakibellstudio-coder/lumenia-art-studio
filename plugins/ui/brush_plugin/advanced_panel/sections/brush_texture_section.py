"""Section 4 & 5: Brush Texture and Spacing."""

from PySide6 import QtWidgets, QtCore
from ui.core.widgets.slider import LabeledSlider
from ui.core.i18n import tr
from typing import TYPE_CHECKING
from ui.core.widgets.collapsible_section import CollapsibleSection
from ..non_scroll_combo_box import NonScrollComboBox

if TYPE_CHECKING:
    from ..panel import AdvancedPanel

def create_brush_texture_section(panel: "AdvancedPanel") -> CollapsibleSection:
    sec = CollapsibleSection(tr("brush.sec_texture", "4. Textura do Pincel (Matéria)"), expanded=True)
    w = QtWidgets.QWidget()
    lo = QtWidgets.QVBoxLayout(w)
    lo.setContentsMargins(0, 0, 0, 0)
    lo.setSpacing(6)

    tex_header = QtWidgets.QHBoxLayout()
    panel.preview_b_grain = QtWidgets.QLabel()
    panel.preview_b_grain.setFixedSize(46, 46)
    panel.preview_b_grain.setObjectName("BTexPreview")
    panel.preview_b_grain.setAlignment(QtCore.Qt.AlignCenter)
    tex_header.addWidget(panel.preview_b_grain)

    tex_info = QtWidgets.QWidget()
    tex_info_lo = QtWidgets.QVBoxLayout(tex_info)
    tex_info_lo.setContentsMargins(4, 0, 0, 0)
    tex_info_lo.setSpacing(4)

    panel.cmb_b_grain = NonScrollComboBox()
    panel.cmb_b_grain.addItems([
        tr("brush.grain_fine", "Grão Fino"),
        tr("brush.grain_watercolor", "Papel Aquarela"),
        tr("brush.grain_oil_canvas", "Tela de Óleo"),
        tr("brush.grain_pure_noise", "Ruído Puro")
    ])
    panel.cmb_b_grain.currentIndexChanged.connect(panel._on_b_grain_preset_changed)

    btn_load_height = QtWidgets.QPushButton(tr("brush.load_texture_png", "Carregar PNG da Textura"))
    btn_load_height.setObjectName("BTexBtn")
    btn_load_height.setFixedHeight(22)
    btn_load_height.setCursor(QtCore.Qt.PointingHandCursor)
    btn_load_height.clicked.connect(panel.loadHeightmapRequested.emit)

    tex_info_lo.addWidget(panel.cmb_b_grain)
    tex_info_lo.addWidget(btn_load_height)
    tex_header.addWidget(tex_info, 1)
    lo.addLayout(tex_header)

    panel.chk_b_grain = QtWidgets.QCheckBox(tr("brush.enable_brush_texture", "Ativar Textura no Pincel"))
    panel.chk_b_grain.setChecked(True)
    panel.chk_b_grain.stateChanged.connect(panel._on_b_grain_enabled)
    lo.addWidget(panel.chk_b_grain)

    panel.sl_b_scale = LabeledSlider(f"{tr('brush.texture_scale', 'Escala da Textura')}:", 10, 500, 100, "%")
    panel.sl_b_scale.valueChanged.connect(panel._on_b_grain_scale)
    lo.addWidget(panel.sl_b_scale)

    panel.slider_contrast = LabeledSlider(f"{tr('brush.texture_contrast', 'Contraste da Textura (Dureza)')}:", 10, 300, 100, "%", param_name="contrast", show_pin=True, default_pinned=False)
    panel.slider_contrast.valueChanged.connect(panel.contrastChanged.emit)
    panel.slider_contrast.valueChanged.connect(panel._on_b_grain_contrast)
    panel.slider_contrast.pinToggled.connect(panel.pinToggled.emit)
    lo.addWidget(panel.slider_contrast)

    panel.chk_invert = QtWidgets.QCheckBox(tr("brush.invert_height", "Inverter Topografia"))
    panel.chk_invert.stateChanged.connect(
        lambda _: panel.invertHeightChanged.emit(panel.chk_invert.isChecked())
    )
    lo.addWidget(panel.chk_invert)

    sec.add_widget(w)
    return sec

def create_spacing_section(panel) -> CollapsibleSection:
    sec = CollapsibleSection(tr("brush.sec_spacing", "5. Espaçamento do Traço"), expanded=True)
    panel.slider_spacing = LabeledSlider(f"{tr('brush.dab_spacing', 'Espaçamento entre Dabs')}:", 1, 100, 10, "%", param_name="spacing", show_pin=True, default_pinned=False)
    panel.slider_spacing.valueChanged.connect(lambda v: panel.spacingChanged.emit(v / 100.0))
    panel.slider_spacing.valueChanged.connect(panel._on_spacing_changed)
    panel.slider_spacing.pinToggled.connect(panel.pinToggled.emit)
    sec.add_widget(panel.slider_spacing)
    return sec
