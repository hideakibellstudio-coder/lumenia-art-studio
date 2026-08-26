"""Smudge Tool Options for Secondary Toolbar."""

from PySide6 import QtCore, QtWidgets
from ui.core.icons import get_icon

def build_smudge_panels(toolbar):
    # Horizontal
    p_h = QtWidgets.QWidget()
    l_h = QtWidgets.QHBoxLayout(p_h)
    l_h.setContentsMargins(0, 0, 0, 0)
    l_h.setSpacing(8)
    l_h.setAlignment(QtCore.Qt.AlignVCenter)

    lbl_i = QtWidgets.QLabel()
    lbl_i.setFixedSize(16, 16)
    lbl_i.setPixmap(get_icon("smudge").pixmap(14, 14))
    l_h.addWidget(lbl_i)

    toolbar.cbo_smudge_preset_h = QtWidgets.QComboBox()
    toolbar.cbo_smudge_preset_h.addItems(["Arrasto Suave", "Mistura de Tinta", "Esfuminho Pesado"])
    toolbar.cbo_smudge_preset_h.setFixedHeight(24)
    toolbar.cbo_smudge_preset_h.currentIndexChanged.connect(lambda idx: toolbar._on_smudge_preset_changed(idx, "h"))
    l_h.addWidget(toolbar.cbo_smudge_preset_h)

    l_h.addWidget(QtWidgets.QLabel("Arrasto:"))
    toolbar.slider_smudge_stretch_h = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_smudge_stretch_h.setRange(1, 100)
    toolbar.slider_smudge_stretch_h.setValue(80)
    toolbar.slider_smudge_stretch_h.setFixedWidth(50)
    toolbar.lbl_smudge_stretch_val_h = QtWidgets.QLabel("80%")
    toolbar.lbl_smudge_stretch_val_h.setStyleSheet("font-size: 11px; font-weight: bold;")
    toolbar.slider_smudge_stretch_h.valueChanged.connect(lambda v: toolbar._on_smudge_stretch_changed(v, "h"))
    l_h.addWidget(toolbar.slider_smudge_stretch_h)
    l_h.addWidget(toolbar.lbl_smudge_stretch_val_h)

    l_h.addWidget(QtWidgets.QLabel("Coleta:"))
    toolbar.slider_smudge_pickup_h = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_smudge_pickup_h.setRange(0, 100)
    toolbar.slider_smudge_pickup_h.setValue(70)
    toolbar.slider_smudge_pickup_h.setFixedWidth(50)
    toolbar.lbl_smudge_pickup_val_h = QtWidgets.QLabel("70%")
    toolbar.lbl_smudge_pickup_val_h.setStyleSheet("font-size: 11px; font-weight: bold;")
    toolbar.slider_smudge_pickup_h.valueChanged.connect(lambda v: toolbar._on_smudge_pickup_changed(v, "h"))
    l_h.addWidget(toolbar.slider_smudge_pickup_h)
    l_h.addWidget(toolbar.lbl_smudge_pickup_val_h)

    l_h.addWidget(QtWidgets.QLabel("Mix:"))
    toolbar.slider_smudge_mix_h = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_smudge_mix_h.setRange(0, 100)
    toolbar.slider_smudge_mix_h.setValue(50)
    toolbar.slider_smudge_mix_h.setFixedWidth(50)
    toolbar.lbl_smudge_mix_val_h = QtWidgets.QLabel("50%")
    toolbar.lbl_smudge_mix_val_h.setStyleSheet("font-size: 11px; font-weight: bold;")
    toolbar.slider_smudge_mix_h.valueChanged.connect(lambda v: toolbar._on_smudge_mix_changed(v, "h"))
    l_h.addWidget(toolbar.slider_smudge_mix_h)
    l_h.addWidget(toolbar.lbl_smudge_mix_val_h)

    # Vertical
    p_v = QtWidgets.QWidget()
    l_v = QtWidgets.QVBoxLayout(p_v)
    l_v.setContentsMargins(0, 0, 0, 0)
    l_v.setSpacing(6)

    h = QtWidgets.QHBoxLayout()
    lbl_iv = QtWidgets.QLabel()
    lbl_iv.setFixedSize(16, 16)
    lbl_iv.setPixmap(get_icon("smudge").pixmap(14, 14))
    h.addWidget(lbl_iv)
    lbl_t = QtWidgets.QLabel("SMUDGE / MISTURA")
    lbl_t.setStyleSheet("font-size: 10px; font-weight: bold; color: #a1a1aa;")
    h.addWidget(lbl_t)
    h.addStretch()
    l_v.addLayout(h)

    toolbar.cbo_smudge_preset_v = QtWidgets.QComboBox()
    toolbar.cbo_smudge_preset_v.addItems(["Arrasto Suave", "Mistura de Tinta", "Esfuminho Pesado"])
    toolbar.cbo_smudge_preset_v.setFixedHeight(24)
    toolbar.cbo_smudge_preset_v.currentIndexChanged.connect(lambda idx: toolbar._on_smudge_preset_changed(idx, "v"))
    l_v.addWidget(toolbar.cbo_smudge_preset_v)

    r1 = QtWidgets.QHBoxLayout()
    r1.addWidget(QtWidgets.QLabel("Alongamento:"))
    r1.addStretch()
    toolbar.lbl_smudge_stretch_val_v = QtWidgets.QLabel("80%")
    toolbar.lbl_smudge_stretch_val_v.setStyleSheet("font-size: 11px; font-weight: bold;")
    r1.addWidget(toolbar.lbl_smudge_stretch_val_v)
    l_v.addLayout(r1)

    toolbar.slider_smudge_stretch_v = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_smudge_stretch_v.setRange(1, 100)
    toolbar.slider_smudge_stretch_v.setValue(80)
    toolbar.slider_smudge_stretch_v.valueChanged.connect(lambda v: toolbar._on_smudge_stretch_changed(v, "v"))
    l_v.addWidget(toolbar.slider_smudge_stretch_v)

    r2 = QtWidgets.QHBoxLayout()
    r2.addWidget(QtWidgets.QLabel("Coleta de Cor:"))
    r2.addStretch()
    toolbar.lbl_smudge_pickup_val_v = QtWidgets.QLabel("70%")
    toolbar.lbl_smudge_pickup_val_v.setStyleSheet("font-size: 11px; font-weight: bold;")
    r2.addWidget(toolbar.lbl_smudge_pickup_val_v)
    l_v.addLayout(r2)

    toolbar.slider_smudge_pickup_v = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_smudge_pickup_v.setRange(0, 100)
    toolbar.slider_smudge_pickup_v.setValue(70)
    toolbar.slider_smudge_pickup_v.valueChanged.connect(lambda v: toolbar._on_smudge_pickup_changed(v, "v"))
    l_v.addWidget(toolbar.slider_smudge_pickup_v)

    r3 = QtWidgets.QHBoxLayout()
    r3.addWidget(QtWidgets.QLabel("Taxa de Mistura:"))
    r3.addStretch()
    toolbar.lbl_smudge_mix_val_v = QtWidgets.QLabel("50%")
    toolbar.lbl_smudge_mix_val_v.setStyleSheet("font-size: 11px; font-weight: bold;")
    r3.addWidget(toolbar.lbl_smudge_mix_val_v)
    l_v.addLayout(r3)

    toolbar.slider_smudge_mix_v = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_smudge_mix_v.setRange(0, 100)
    toolbar.slider_smudge_mix_v.setValue(50)
    toolbar.slider_smudge_mix_v.valueChanged.connect(lambda v: toolbar._on_smudge_mix_changed(v, "v"))
    l_v.addWidget(toolbar.slider_smudge_mix_v)

    toolbar.stacked_widget.addWidget(p_h)
    toolbar.stacked_widget.addWidget(p_v)
    toolbar._panels_h["smudge"] = p_h
    toolbar._panels_v["smudge"] = p_v
