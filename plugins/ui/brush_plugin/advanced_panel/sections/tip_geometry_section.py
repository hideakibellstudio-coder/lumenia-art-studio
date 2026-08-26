"""Section 2: Brush Tip Geometry."""

from PySide6 import QtWidgets, QtCore
from ui.core.widgets.slider import LabeledSlider
from ..collapsible_section import CollapsibleSection
from ..non_scroll_combo_box import NonScrollComboBox

def create_tip_geometry_section(panel) -> CollapsibleSection:
    sec = CollapsibleSection("2. Geometria da Ponta", expanded=True)
    w = QtWidgets.QWidget()
    lo = QtWidgets.QVBoxLayout(w)
    lo.setContentsMargins(0, 0, 0, 0)
    lo.setSpacing(6)

    tip_header = QtWidgets.QHBoxLayout()
    panel.shape_preview = QtWidgets.QLabel()
    panel.shape_preview.setFixedSize(46, 46)
    panel.shape_preview.setObjectName("BTexPreview")
    panel.shape_preview.setAlignment(QtCore.Qt.AlignCenter)
    tip_header.addWidget(panel.shape_preview)

    tip_info = QtWidgets.QWidget()
    tip_info_lo = QtWidgets.QVBoxLayout(tip_info)
    tip_info_lo.setContentsMargins(4, 0, 0, 0)
    tip_info_lo.setSpacing(4)

    panel.cmb_shape = NonScrollComboBox()
    panel.cmb_shape.addItems(["Ponta Suave (Radial)", "Ponta Dura (Circular)", "Cerdas Secas", "Quadrado / Chato"])
    panel.cmb_shape.currentIndexChanged.connect(panel._on_shape_preset_changed)

    btn_load_shape = QtWidgets.QPushButton("Carregar PNG da Ponta")
    btn_load_shape.setObjectName("BTexBtn")
    btn_load_shape.setFixedHeight(22)
    btn_load_shape.setCursor(QtCore.Qt.PointingHandCursor)
    btn_load_shape.clicked.connect(panel.loadShapeRequested.emit)

    tip_info_lo.addWidget(panel.cmb_shape)
    tip_info_lo.addWidget(btn_load_shape)
    tip_header.addWidget(tip_info, 1)
    lo.addLayout(tip_header)

    panel.sl_hardness = LabeledSlider("Dureza da Ponta (Hardness):", 0, 100, 100, "%")
    panel.sl_hardness.valueChanged.connect(panel._on_tip_hardness)
    lo.addWidget(panel.sl_hardness)

    panel.sl_angle = LabeledSlider("Ângulo da Ponta:", 0, 360, 0, "°")
    panel.sl_angle.valueChanged.connect(panel._on_tip_angle)
    lo.addWidget(panel.sl_angle)

    panel.sl_press_angle = LabeledSlider("Ângulo por Pressão:", 0, 360, 0, "°")
    panel.sl_press_angle.valueChanged.connect(panel._on_press_angle)
    lo.addWidget(panel.sl_press_angle)

    panel.sl_aspect = LabeledSlider("Elipse / Proporção:", 1, 100, 100, "%")
    panel.sl_aspect.valueChanged.connect(panel._on_tip_aspect)
    lo.addWidget(panel.sl_aspect)

    panel.chk_follow = QtWidgets.QCheckBox("Seguir Direção do Traço (Follow Stroke)")
    panel.chk_follow.stateChanged.connect(panel._on_tip_follow)
    lo.addWidget(panel.chk_follow)

    sec.add_widget(w)
    return sec
