"""Shapes Tool Options for Secondary Toolbar."""

from PySide6 import QtCore, QtWidgets
from ui.core.icons import get_icon
from ui.core.widgets.shape_dropdown import ShapeDropdown

def build_shapes_panels(toolbar):
    # Horizontal
    p_h = QtWidgets.QWidget()
    l_h = QtWidgets.QHBoxLayout(p_h)
    l_h.setContentsMargins(0, 0, 0, 0)
    l_h.setSpacing(8)
    l_h.setAlignment(QtCore.Qt.AlignVCenter)

    toolbar.shape_dropdown_h = ShapeDropdown()
    toolbar.shape_dropdown_h.setFixedHeight(24)
    toolbar.shape_dropdown_h.set_shape("shape_line", "Linha Reta")
    toolbar.shape_dropdown_h.shape_changed.connect(lambda sid, lbl: toolbar._on_shape_type_changed(sid, lbl, "h"))
    l_h.addWidget(toolbar.shape_dropdown_h)

    toolbar.cbo_shape_mode_h = QtWidgets.QComboBox()
    toolbar.cbo_shape_mode_h.addItems(["Contorno & Fill", "Apenas Contorno", "Apenas Fill"])
    toolbar.cbo_shape_mode_h.setFixedHeight(24)
    toolbar.cbo_shape_mode_h.currentIndexChanged.connect(lambda idx: toolbar._on_shape_mode_changed(idx, "h"))
    l_h.addWidget(toolbar.cbo_shape_mode_h)

    l_h.addWidget(QtWidgets.QLabel("Traço:"))
    toolbar.slider_shape_stroke_h = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_shape_stroke_h.setRange(1, 100)
    toolbar.slider_shape_stroke_h.setValue(4)
    toolbar.slider_shape_stroke_h.setFixedWidth(50)
    toolbar.lbl_shape_stroke_val_h = QtWidgets.QLabel("4px")
    toolbar.lbl_shape_stroke_val_h.setStyleSheet("font-size: 11px; font-weight: bold;")
    toolbar.slider_shape_stroke_h.valueChanged.connect(lambda v: toolbar._on_shape_stroke_changed(v, "h"))
    l_h.addWidget(toolbar.slider_shape_stroke_h)
    l_h.addWidget(toolbar.lbl_shape_stroke_val_h)

    l_h.addWidget(QtWidgets.QLabel("Borda:"))
    toolbar.btn_shape_stroke_col_h = QtWidgets.QPushButton()
    toolbar.btn_shape_stroke_col_h.setFixedSize(20, 20)
    toolbar.btn_shape_stroke_col_h.setStyleSheet("background: #000000; border-radius: 4px; border: 1px solid rgba(255,255,255,0.4);")
    toolbar.btn_shape_stroke_col_h.clicked.connect(toolbar._pick_shape_stroke_color)
    l_h.addWidget(toolbar.btn_shape_stroke_col_h)

    l_h.addWidget(QtWidgets.QLabel("Fundo:"))
    toolbar.btn_shape_fill_col_h = QtWidgets.QPushButton()
    toolbar.btn_shape_fill_col_h.setFixedSize(20, 20)
    toolbar.btn_shape_fill_col_h.setStyleSheet("background: #000000; border-radius: 4px; border: 1px solid rgba(255,255,255,0.4);")
    toolbar.btn_shape_fill_col_h.clicked.connect(toolbar._pick_shape_fill_color)
    l_h.addWidget(toolbar.btn_shape_fill_col_h)

    l_h.addWidget(QtWidgets.QLabel("Opac:"))
    toolbar.slider_shape_fill_opac_h = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_shape_fill_opac_h.setRange(0, 100)
    toolbar.slider_shape_fill_opac_h.setValue(100)
    toolbar.slider_shape_fill_opac_h.setFixedWidth(45)
    toolbar.lbl_shape_fill_opac_val_h = QtWidgets.QLabel("100%")
    toolbar.lbl_shape_fill_opac_val_h.setStyleSheet("font-size: 11px; font-weight: bold;")
    toolbar.slider_shape_fill_opac_h.valueChanged.connect(lambda v: toolbar._on_shape_fill_opac_changed(v, "h"))
    l_h.addWidget(toolbar.slider_shape_fill_opac_h)
    l_h.addWidget(toolbar.lbl_shape_fill_opac_val_h)

    toolbar.lbl_shape_extra_h = QtWidgets.QLabel("Raio:")
    toolbar.lbl_shape_extra_h.setStyleSheet("font-size: 11px; color: #a1a1aa;")
    toolbar.slider_shape_extra_h = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_shape_extra_h.setRange(0, 100)
    toolbar.slider_shape_extra_h.setValue(0)
    toolbar.slider_shape_extra_h.setFixedWidth(45)
    toolbar.lbl_shape_extra_val_h = QtWidgets.QLabel("0px")
    toolbar.lbl_shape_extra_val_h.setStyleSheet("font-size: 11px; font-weight: bold;")
    toolbar.slider_shape_extra_h.valueChanged.connect(lambda v: toolbar._on_shape_extra_changed(v, "h"))
    l_h.addWidget(toolbar.lbl_shape_extra_h)
    l_h.addWidget(toolbar.slider_shape_extra_h)
    l_h.addWidget(toolbar.lbl_shape_extra_val_h)

    toolbar.lbl_shape_extra_h.hide()
    toolbar.slider_shape_extra_h.hide()
    toolbar.lbl_shape_extra_val_h.hide()

    # Vertical
    p_v = QtWidgets.QWidget()
    l_v = QtWidgets.QVBoxLayout(p_v)
    l_v.setContentsMargins(0, 0, 0, 0)
    l_v.setSpacing(6)

    h = QtWidgets.QHBoxLayout()
    toolbar.lbl_shape_icon_v = QtWidgets.QLabel()
    toolbar.lbl_shape_icon_v.setFixedSize(16, 16)
    toolbar.lbl_shape_icon_v.setPixmap(get_icon("shape_line").pixmap(14, 14))
    h.addWidget(toolbar.lbl_shape_icon_v)
    lbl_t = QtWidgets.QLabel("FORMAS VETORIAIS")
    lbl_t.setStyleSheet("font-size: 10px; font-weight: bold; color: #a1a1aa;")
    h.addWidget(lbl_t)
    h.addStretch()
    l_v.addLayout(h)

    toolbar.shape_dropdown_v = ShapeDropdown()
    toolbar.shape_dropdown_v.setFixedHeight(24)
    toolbar.shape_dropdown_v.set_shape("shape_line", "Linha Reta")
    toolbar.shape_dropdown_v.shape_changed.connect(lambda sid, lbl: toolbar._on_shape_type_changed(sid, lbl, "v"))
    l_v.addWidget(toolbar.shape_dropdown_v)

    toolbar.cbo_shape_mode_v = QtWidgets.QComboBox()
    toolbar.cbo_shape_mode_v.addItems(["Contorno & Fill", "Apenas Contorno", "Apenas Fill"])
    toolbar.cbo_shape_mode_v.setFixedHeight(24)
    toolbar.cbo_shape_mode_v.currentIndexChanged.connect(lambda idx: toolbar._on_shape_mode_changed(idx, "v"))
    l_v.addWidget(toolbar.cbo_shape_mode_v)

    r1 = QtWidgets.QHBoxLayout()
    r1.addWidget(QtWidgets.QLabel("Traço:"))
    r1.addStretch()
    toolbar.lbl_shape_stroke_val_v = QtWidgets.QLabel("4px")
    toolbar.lbl_shape_stroke_val_v.setStyleSheet("font-size: 11px; font-weight: bold;")
    r1.addWidget(toolbar.lbl_shape_stroke_val_v)
    l_v.addLayout(r1)

    toolbar.slider_shape_stroke_v = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_shape_stroke_v.setRange(1, 100)
    toolbar.slider_shape_stroke_v.setValue(4)
    toolbar.slider_shape_stroke_v.valueChanged.connect(lambda v: toolbar._on_shape_stroke_changed(v, "v"))
    l_v.addWidget(toolbar.slider_shape_stroke_v)

    r_col = QtWidgets.QHBoxLayout()
    r_col.addWidget(QtWidgets.QLabel("Borda:"))
    toolbar.btn_shape_stroke_col_v = QtWidgets.QPushButton()
    toolbar.btn_shape_stroke_col_v.setFixedSize(20, 20)
    toolbar.btn_shape_stroke_col_v.setStyleSheet("background: #000000; border-radius: 4px; border: 1px solid rgba(255,255,255,0.4);")
    toolbar.btn_shape_stroke_col_v.clicked.connect(toolbar._pick_shape_stroke_color)
    r_col.addWidget(toolbar.btn_shape_stroke_col_v)

    r_col.addWidget(QtWidgets.QLabel("Fundo:"))
    toolbar.btn_shape_fill_col_v = QtWidgets.QPushButton()
    toolbar.btn_shape_fill_col_v.setFixedSize(20, 20)
    toolbar.btn_shape_fill_col_v.setStyleSheet("background: #000000; border-radius: 4px; border: 1px solid rgba(255,255,255,0.4);")
    toolbar.btn_shape_fill_col_v.clicked.connect(toolbar._pick_shape_fill_color)
    r_col.addWidget(toolbar.btn_shape_fill_col_v)
    r_col.addStretch()
    l_v.addLayout(r_col)

    r2 = QtWidgets.QHBoxLayout()
    r2.addWidget(QtWidgets.QLabel("Opac. Fundo:"))
    r2.addStretch()
    toolbar.lbl_shape_fill_opac_val_v = QtWidgets.QLabel("100%")
    toolbar.lbl_shape_fill_opac_val_v.setStyleSheet("font-size: 11px; font-weight: bold;")
    r2.addWidget(toolbar.lbl_shape_fill_opac_val_v)
    l_v.addLayout(r2)

    toolbar.slider_shape_fill_opac_v = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_shape_fill_opac_v.setRange(0, 100)
    toolbar.slider_shape_fill_opac_v.setValue(100)
    toolbar.slider_shape_fill_opac_v.valueChanged.connect(lambda v: toolbar._on_shape_fill_opac_changed(v, "v"))
    l_v.addWidget(toolbar.slider_shape_fill_opac_v)

    toolbar.row_shape_extra_v = QtWidgets.QHBoxLayout()
    toolbar.lbl_shape_extra_v = QtWidgets.QLabel("Raio:")
    toolbar.lbl_shape_extra_v.setStyleSheet("font-size: 11px; color: #a1a1aa;")
    toolbar.row_shape_extra_v.addWidget(toolbar.lbl_shape_extra_v)
    toolbar.row_shape_extra_v.addStretch()
    toolbar.lbl_shape_extra_val_v = QtWidgets.QLabel("0px")
    toolbar.lbl_shape_extra_val_v.setStyleSheet("font-size: 11px; font-weight: bold;")
    toolbar.row_shape_extra_v.addWidget(toolbar.lbl_shape_extra_val_v)
    l_v.addLayout(toolbar.row_shape_extra_v)

    toolbar.slider_shape_extra_v = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_shape_extra_v.setRange(0, 100)
    toolbar.slider_shape_extra_v.setValue(0)
    toolbar.slider_shape_extra_v.valueChanged.connect(lambda v: toolbar._on_shape_extra_changed(v, "v"))
    l_v.addWidget(toolbar.slider_shape_extra_v)

    toolbar.lbl_shape_extra_v.hide()
    toolbar.slider_shape_extra_v.hide()
    toolbar.lbl_shape_extra_val_v.hide()

    toolbar.stacked_widget.addWidget(p_h)
    toolbar.stacked_widget.addWidget(p_v)
    toolbar._panels_h["shapes"] = p_h
    toolbar._panels_v["shapes"] = p_v
    for st in ["shape_rect", "shape_ellipse", "shape_line", "shape_polygon", "shape_star"]:
        toolbar._panels_h[st] = p_h
        toolbar._panels_v[st] = p_v
