"""Eyedropper Tool Options for Secondary Toolbar."""

from PySide6 import QtCore, QtWidgets
from ui.core.icons import get_icon

def build_eyedrop_panels(toolbar):
    # Horizontal
    p_h = QtWidgets.QWidget()
    l_h = QtWidgets.QHBoxLayout(p_h)
    l_h.setContentsMargins(0, 0, 0, 0)
    l_h.setSpacing(8)
    l_h.setAlignment(QtCore.Qt.AlignVCenter)

    lbl_i = QtWidgets.QLabel()
    lbl_i.setFixedSize(16, 16)
    lbl_i.setPixmap(get_icon("eyedrop").pixmap(14, 14))
    l_h.addWidget(lbl_i)

    toolbar.cbo_sample_h = QtWidgets.QComboBox()
    toolbar.cbo_sample_h.addItems(["1x1 Ponto", "3x3 Média", "5x5 Média", "11x11 Média"])
    toolbar.cbo_sample_h.setFixedHeight(24)
    toolbar.cbo_sample_h.currentIndexChanged.connect(lambda idx: toolbar._on_eyedrop_sample_changed(idx, "h"))
    l_h.addWidget(toolbar.cbo_sample_h)

    toolbar.btn_eye_merged_h = QtWidgets.QToolButton()
    toolbar.btn_eye_merged_h.setText("Todas Camadas")
    toolbar.btn_eye_merged_h.setCheckable(True)
    toolbar.btn_eye_merged_h.setChecked(True)
    toolbar.btn_eye_merged_h.setFixedHeight(24)
    toolbar.btn_eye_merged_h.toggled.connect(lambda v: toolbar._on_eyedrop_merged_changed(v, "h"))
    l_h.addWidget(toolbar.btn_eye_merged_h)

    toolbar.swatch_h = QtWidgets.QLabel()
    toolbar.swatch_h.setFixedSize(20, 20)
    toolbar.swatch_h.setStyleSheet("background: #000000; border-radius: 4px; border: 1px solid rgba(255,255,255,0.3);")
    l_h.addWidget(toolbar.swatch_h)

    toolbar.lbl_hex_h = QtWidgets.QLabel("#000000")
    toolbar.lbl_hex_h.setStyleSheet("font-size: 11px; font-weight: bold;")
    l_h.addWidget(toolbar.lbl_hex_h)

    # Vertical
    p_v = QtWidgets.QWidget()
    l_v = QtWidgets.QVBoxLayout(p_v)
    l_v.setContentsMargins(0, 0, 0, 0)
    l_v.setSpacing(6)

    h = QtWidgets.QHBoxLayout()
    lbl_iv = QtWidgets.QLabel()
    lbl_iv.setFixedSize(16, 16)
    lbl_iv.setPixmap(get_icon("eyedrop").pixmap(14, 14))
    h.addWidget(lbl_iv)
    lbl_t = QtWidgets.QLabel("CONTA-GOTAS")
    lbl_t.setProperty("heading", "true")
    h.addWidget(lbl_t)
    h.addStretch()
    l_v.addLayout(h)

    toolbar.cbo_sample_v = QtWidgets.QComboBox()
    toolbar.cbo_sample_v.addItems(["1x1 Ponto", "3x3 Média", "5x5 Média", "11x11 Média"])
    toolbar.cbo_sample_v.setFixedHeight(24)
    toolbar.cbo_sample_v.currentIndexChanged.connect(lambda idx: toolbar._on_eyedrop_sample_changed(idx, "v"))
    l_v.addWidget(toolbar.cbo_sample_v)

    toolbar.btn_eye_merged_v = QtWidgets.QToolButton()
    toolbar.btn_eye_merged_v.setText("Todas Camadas")
    toolbar.btn_eye_merged_v.setCheckable(True)
    toolbar.btn_eye_merged_v.setChecked(True)
    toolbar.btn_eye_merged_v.setFixedHeight(24)
    toolbar.btn_eye_merged_v.toggled.connect(lambda v: toolbar._on_eyedrop_merged_changed(v, "v"))
    l_v.addWidget(toolbar.btn_eye_merged_v)

    r = QtWidgets.QHBoxLayout()
    r.addWidget(QtWidgets.QLabel("Cor:"))
    toolbar.swatch_v = QtWidgets.QLabel()
    toolbar.swatch_v.setFixedSize(20, 20)
    toolbar.swatch_v.setStyleSheet("background: #000000; border-radius: 4px; border: 1px solid rgba(255,255,255,0.3);")
    r.addWidget(toolbar.swatch_v)
    toolbar.lbl_hex_v = QtWidgets.QLabel("#000000")
    toolbar.lbl_hex_v.setStyleSheet("font-size: 11px; font-weight: bold;")
    r.addWidget(toolbar.lbl_hex_v)
    r.addStretch()
    l_v.addLayout(r)

    toolbar.stacked_widget.addWidget(p_h)
    toolbar.stacked_widget.addWidget(p_v)
    toolbar.panels_h["eyedrop"] = p_h
    toolbar.panels_v["eyedrop"] = p_v
