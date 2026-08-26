"""Magic Wand Tool Options for Secondary Toolbar."""

from PySide6 import QtCore, QtWidgets
from ui.core.icons import get_icon

def build_wand_panels(toolbar):
    # Horizontal
    p_h = QtWidgets.QWidget()
    l_h = QtWidgets.QHBoxLayout(p_h)
    l_h.setContentsMargins(0, 0, 0, 0)
    l_h.setSpacing(8)
    l_h.setAlignment(QtCore.Qt.AlignVCenter)

    lbl_i = QtWidgets.QLabel()
    lbl_i.setFixedSize(16, 16)
    lbl_i.setPixmap(get_icon("wand").pixmap(14, 14))
    l_h.addWidget(lbl_i)

    l_h.addWidget(QtWidgets.QLabel("Tol:"))
    toolbar.slider_wand_tol_h = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_wand_tol_h.setRange(0, 100)
    toolbar.slider_wand_tol_h.setValue(20)
    toolbar.slider_wand_tol_h.setFixedWidth(55)
    toolbar.lbl_wand_tol_val_h = QtWidgets.QLabel("20%")
    toolbar.lbl_wand_tol_val_h.setStyleSheet("font-size: 11px; font-weight: bold;")
    toolbar.slider_wand_tol_h.valueChanged.connect(lambda v: toolbar._on_wand_tol_changed(v, "h"))
    l_h.addWidget(toolbar.slider_wand_tol_h)
    l_h.addWidget(toolbar.lbl_wand_tol_val_h)

    toolbar.btn_wand_contig_h = QtWidgets.QToolButton()
    toolbar.btn_wand_contig_h.setText("Contíguo")
    toolbar.btn_wand_contig_h.setCheckable(True)
    toolbar.btn_wand_contig_h.setChecked(True)
    toolbar.btn_wand_contig_h.setFixedHeight(24)
    toolbar.btn_wand_contig_h.toggled.connect(lambda v: toolbar._on_wand_contig_changed(v, "h"))
    l_h.addWidget(toolbar.btn_wand_contig_h)

    toolbar.btn_wand_merged_h = QtWidgets.QToolButton()
    toolbar.btn_wand_merged_h.setText("Todas Camadas")
    toolbar.btn_wand_merged_h.setCheckable(True)
    toolbar.btn_wand_merged_h.setChecked(True)
    toolbar.btn_wand_merged_h.setFixedHeight(24)
    toolbar.btn_wand_merged_h.toggled.connect(lambda v: toolbar._on_wand_merged_changed(v, "h"))
    l_h.addWidget(toolbar.btn_wand_merged_h)

    toolbar.cbo_wand_mode_h = QtWidgets.QComboBox()
    toolbar.cbo_wand_mode_h.addItems(["Nova Seleção", "Adicionar (+)", "Subtrair (-)", "Interseção"])
    toolbar.cbo_wand_mode_h.setFixedHeight(24)
    toolbar.cbo_wand_mode_h.currentIndexChanged.connect(lambda idx: toolbar._on_wand_mode_changed(idx, "h"))
    l_h.addWidget(toolbar.cbo_wand_mode_h)

    toolbar.btn_wand_deselect_h = QtWidgets.QToolButton()
    toolbar.btn_wand_deselect_h.setIcon(get_icon("deselect"))
    toolbar.btn_wand_deselect_h.setText(" Desmarcar")
    toolbar.btn_wand_deselect_h.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    toolbar.btn_wand_deselect_h.setFixedHeight(24)
    toolbar.btn_wand_deselect_h.clicked.connect(toolbar._on_deselect_clicked)
    l_h.addWidget(toolbar.btn_wand_deselect_h)

    # Vertical
    p_v = QtWidgets.QWidget()
    l_v = QtWidgets.QVBoxLayout(p_v)
    l_v.setContentsMargins(0, 0, 0, 0)
    l_v.setSpacing(6)

    h = QtWidgets.QHBoxLayout()
    lbl_iv = QtWidgets.QLabel()
    lbl_iv.setFixedSize(16, 16)
    lbl_iv.setPixmap(get_icon("wand").pixmap(14, 14))
    h.addWidget(lbl_iv)
    lbl_t = QtWidgets.QLabel("VARINHA MÁGICA")
    lbl_t.setStyleSheet("font-size: 10px; font-weight: bold; color: #a1a1aa;")
    h.addWidget(lbl_t)
    h.addStretch()
    l_v.addLayout(h)

    r1 = QtWidgets.QHBoxLayout()
    r1.addWidget(QtWidgets.QLabel("Tolerância:"))
    r1.addStretch()
    toolbar.lbl_wand_tol_val_v = QtWidgets.QLabel("20%")
    toolbar.lbl_wand_tol_val_v.setStyleSheet("font-size: 11px; font-weight: bold;")
    r1.addWidget(toolbar.lbl_wand_tol_val_v)
    l_v.addLayout(r1)

    toolbar.slider_wand_tol_v = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    toolbar.slider_wand_tol_v.setRange(0, 100)
    toolbar.slider_wand_tol_v.setValue(20)
    toolbar.slider_wand_tol_v.valueChanged.connect(lambda v: toolbar._on_wand_tol_changed(v, "v"))
    l_v.addWidget(toolbar.slider_wand_tol_v)

    row_btns = QtWidgets.QHBoxLayout()
    toolbar.btn_wand_contig_v = QtWidgets.QToolButton()
    toolbar.btn_wand_contig_v.setText("Contíguo")
    toolbar.btn_wand_contig_v.setCheckable(True)
    toolbar.btn_wand_contig_v.setChecked(True)
    toolbar.btn_wand_contig_v.setFixedHeight(24)
    toolbar.btn_wand_contig_v.toggled.connect(lambda v: toolbar._on_wand_contig_changed(v, "v"))
    row_btns.addWidget(toolbar.btn_wand_contig_v)

    toolbar.btn_wand_merged_v = QtWidgets.QToolButton()
    toolbar.btn_wand_merged_v.setText("Todas Camadas")
    toolbar.btn_wand_merged_v.setCheckable(True)
    toolbar.btn_wand_merged_v.setChecked(True)
    toolbar.btn_wand_merged_v.setFixedHeight(24)
    toolbar.btn_wand_merged_v.toggled.connect(lambda v: toolbar._on_wand_merged_changed(v, "v"))
    row_btns.addWidget(toolbar.btn_wand_merged_v)
    l_v.addLayout(row_btns)

    toolbar.cbo_wand_mode_v = QtWidgets.QComboBox()
    toolbar.cbo_wand_mode_v.addItems(["Nova Seleção", "Adicionar (+)", "Subtrair (-)", "Interseção"])
    toolbar.cbo_wand_mode_v.setFixedHeight(24)
    toolbar.cbo_wand_mode_v.currentIndexChanged.connect(lambda idx: toolbar._on_wand_mode_changed(idx, "v"))
    l_v.addWidget(toolbar.cbo_wand_mode_v)

    toolbar.btn_wand_deselect_v = QtWidgets.QToolButton()
    toolbar.btn_wand_deselect_v.setIcon(get_icon("deselect"))
    toolbar.btn_wand_deselect_v.setText(" Desmarcar")
    toolbar.btn_wand_deselect_v.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    toolbar.btn_wand_deselect_v.setFixedHeight(24)
    toolbar.btn_wand_deselect_v.clicked.connect(toolbar._on_deselect_clicked)
    l_v.addWidget(toolbar.btn_wand_deselect_v)

    toolbar.stacked_widget.addWidget(p_h)
    toolbar.stacked_widget.addWidget(p_v)
    toolbar._panels_h["wand"] = p_h
    toolbar._panels_v["wand"] = p_v
