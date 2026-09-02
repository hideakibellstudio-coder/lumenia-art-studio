"""Geometric Selection (Rect / Ellipse) Tool Options for Secondary Toolbar."""

from PySide6 import QtCore, QtWidgets
from ui.core.icons import get_icon

def build_geom_panels(toolbar):
    # Horizontal
    p_h = QtWidgets.QWidget()
    l_h = QtWidgets.QHBoxLayout(p_h)
    l_h.setContentsMargins(0, 0, 0, 0)
    l_h.setSpacing(8)
    l_h.setAlignment(QtCore.Qt.AlignVCenter)

    toolbar.lbl_geom_icon_h = QtWidgets.QLabel()
    toolbar.lbl_geom_icon_h.setFixedSize(16, 16)
    toolbar.lbl_geom_icon_h.setPixmap(get_icon("select_rect").pixmap(14, 14))
    l_h.addWidget(toolbar.lbl_geom_icon_h)

    l_h.addWidget(QtWidgets.QLabel("Feather:"))
    toolbar.slider_geom_feather_h = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_geom_feather_h.setRange(0, 50)
    toolbar.slider_geom_feather_h.setValue(0)
    toolbar.slider_geom_feather_h.setFixedWidth(50)
    toolbar.lbl_geom_feather_val_h = QtWidgets.QLabel("0px")
    toolbar.lbl_geom_feather_val_h.setStyleSheet("font-size: 11px; font-weight: bold;")
    toolbar.slider_geom_feather_h.valueChanged.connect(lambda v: toolbar._on_geom_feather_changed(v, "h"))
    l_h.addWidget(toolbar.slider_geom_feather_h)
    l_h.addWidget(toolbar.lbl_geom_feather_val_h)

    toolbar.btn_geom_aa_h = QtWidgets.QToolButton()
    toolbar.btn_geom_aa_h.setText("Anti-Alias")
    toolbar.btn_geom_aa_h.setCheckable(True)
    toolbar.btn_geom_aa_h.setChecked(True)
    toolbar.btn_geom_aa_h.setFixedHeight(24)
    toolbar.btn_geom_aa_h.toggled.connect(lambda v: toolbar._on_geom_aa_changed(v, "h"))
    l_h.addWidget(toolbar.btn_geom_aa_h)

    toolbar.cbo_geom_mode_h = QtWidgets.QComboBox()
    toolbar.cbo_geom_mode_h.addItems(["Nova Seleção", "Adicionar (+)", "Subtrair (-)", "Interseção"])
    toolbar.cbo_geom_mode_h.setFixedHeight(24)
    toolbar.cbo_geom_mode_h.currentIndexChanged.connect(lambda idx: toolbar._on_geom_mode_changed(idx, "h"))
    l_h.addWidget(toolbar.cbo_geom_mode_h)

    toolbar.btn_geom_deselect_h = QtWidgets.QToolButton()
    toolbar.btn_geom_deselect_h.setIcon(get_icon("deselect"))
    toolbar.btn_geom_deselect_h.setText(" Desmarcar")
    toolbar.btn_geom_deselect_h.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    toolbar.btn_geom_deselect_h.setFixedHeight(24)
    toolbar.btn_geom_deselect_h.clicked.connect(toolbar._on_deselect_clicked)
    l_h.addWidget(toolbar.btn_geom_deselect_h)

    # Vertical
    p_v = QtWidgets.QWidget()
    l_v = QtWidgets.QVBoxLayout(p_v)
    l_v.setContentsMargins(0, 0, 0, 0)
    l_v.setSpacing(6)

    h = QtWidgets.QHBoxLayout()
    toolbar.lbl_geom_icon_v = QtWidgets.QLabel()
    toolbar.lbl_geom_icon_v.setFixedSize(16, 16)
    toolbar.lbl_geom_icon_v.setPixmap(get_icon("select_rect").pixmap(14, 14))
    h.addWidget(toolbar.lbl_geom_icon_v)
    lbl_t = QtWidgets.QLabel("SELEÇÃO")
    lbl_t.setProperty("heading", "true")
    h.addWidget(lbl_t)
    h.addStretch()
    l_v.addLayout(h)

    r1 = QtWidgets.QHBoxLayout()
    r1.addWidget(QtWidgets.QLabel("Feather:"))
    r1.addStretch()
    toolbar.lbl_geom_feather_val_v = QtWidgets.QLabel("0px")
    toolbar.lbl_geom_feather_val_v.setStyleSheet("font-size: 11px; font-weight: bold;")
    r1.addWidget(toolbar.lbl_geom_feather_val_v)
    l_v.addLayout(r1)

    toolbar.slider_geom_feather_v = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_geom_feather_v.setRange(0, 50)
    toolbar.slider_geom_feather_v.setValue(0)
    toolbar.slider_geom_feather_v.valueChanged.connect(lambda v: toolbar._on_geom_feather_changed(v, "v"))
    l_v.addWidget(toolbar.slider_geom_feather_v)

    row_btns = QtWidgets.QHBoxLayout()
    toolbar.btn_geom_aa_v = QtWidgets.QToolButton()
    toolbar.btn_geom_aa_v.setText("Anti-Alias")
    toolbar.btn_geom_aa_v.setCheckable(True)
    toolbar.btn_geom_aa_v.setChecked(True)
    toolbar.btn_geom_aa_v.setFixedHeight(24)
    toolbar.btn_geom_aa_v.toggled.connect(lambda v: toolbar._on_geom_aa_changed(v, "v"))
    row_btns.addWidget(toolbar.btn_geom_aa_v)

    toolbar.btn_geom_deselect_v = QtWidgets.QToolButton()
    toolbar.btn_geom_deselect_v.setIcon(get_icon("deselect"))
    toolbar.btn_geom_deselect_v.setText(" Desmarcar")
    toolbar.btn_geom_deselect_v.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    toolbar.btn_geom_deselect_v.setFixedHeight(24)
    toolbar.btn_geom_deselect_v.clicked.connect(toolbar._on_deselect_clicked)
    row_btns.addWidget(toolbar.btn_geom_deselect_v)
    l_v.addLayout(row_btns)

    toolbar.cbo_geom_mode_v = QtWidgets.QComboBox()
    toolbar.cbo_geom_mode_v.addItems(["Nova Seleção", "Adicionar (+)", "Subtrair (-)", "Interseção"])
    toolbar.cbo_geom_mode_v.setFixedHeight(24)
    toolbar.cbo_geom_mode_v.currentIndexChanged.connect(lambda idx: toolbar._on_geom_mode_changed(idx, "v"))
    l_v.addWidget(toolbar.cbo_geom_mode_v)

    toolbar.stacked_widget.addWidget(p_h)
    toolbar.stacked_widget.addWidget(p_v)
    toolbar._panels_h["rect_select"] = p_h
    toolbar._panels_v["rect_select"] = p_v
    toolbar._panels_h["ellipse_select"] = p_h
    toolbar._panels_v["ellipse_select"] = p_v
