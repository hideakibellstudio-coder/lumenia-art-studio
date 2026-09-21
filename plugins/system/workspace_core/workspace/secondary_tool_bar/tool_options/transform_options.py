"""Transform Tool Options for Secondary Toolbar."""

from typing import TYPE_CHECKING
from PySide6 import QtCore, QtWidgets
from ui.core.icons import get_icon
from ui.core.theme.manager import ThemeManager

if TYPE_CHECKING:
    from ..toolbar import SecondaryToolBar

def build_transform_panels(toolbar: "SecondaryToolBar"):
    # Horizontal
    p_h = QtWidgets.QWidget()
    l_h = QtWidgets.QHBoxLayout(p_h)
    l_h.setContentsMargins(0, 0, 0, 0)
    l_h.setSpacing(8)
    l_h.setAlignment(QtCore.Qt.AlignVCenter)

    toolbar.btn_trans_commit_h = QtWidgets.QToolButton()
    toolbar.btn_trans_commit_h.setObjectName("successButton")
    toolbar.btn_trans_commit_h.setText("Aplicar")
    toolbar.btn_trans_commit_h.setIcon(get_icon("check", ThemeManager.instance().get_color("text_main")))
    toolbar.btn_trans_commit_h.setFixedHeight(24)
    toolbar.btn_trans_commit_h.clicked.connect(toolbar._on_transform_commit_clicked)
    l_h.addWidget(toolbar.btn_trans_commit_h)

    toolbar.btn_trans_cancel_h = QtWidgets.QToolButton()
    toolbar.btn_trans_cancel_h.setText("Cancelar")
    toolbar.btn_trans_cancel_h.setIcon(get_icon("close", ThemeManager.instance().get_color("text_main")))
    toolbar.btn_trans_cancel_h.setFixedHeight(24)
    toolbar.btn_trans_cancel_h.clicked.connect(toolbar._on_transform_cancel_clicked)
    l_h.addWidget(toolbar.btn_trans_cancel_h)

    toolbar.btn_trans_flip_h_h = QtWidgets.QToolButton()
    toolbar.btn_trans_flip_h_h.setText("Espelhar H")
    toolbar.btn_trans_flip_h_h.setFixedHeight(24)
    toolbar.btn_trans_flip_h_h.clicked.connect(toolbar._on_transform_flip_h_clicked)
    l_h.addWidget(toolbar.btn_trans_flip_h_h)

    toolbar.btn_trans_flip_v_h = QtWidgets.QToolButton()
    toolbar.btn_trans_flip_v_h.setText("Espelhar V")
    toolbar.btn_trans_flip_v_h.setFixedHeight(24)
    toolbar.btn_trans_flip_v_h.clicked.connect(toolbar._on_transform_flip_v_clicked)
    l_h.addWidget(toolbar.btn_trans_flip_v_h)

    toolbar.btn_trans_rot_90_h = QtWidgets.QToolButton()
    toolbar.btn_trans_rot_90_h.setText("Girar 90°")
    toolbar.btn_trans_rot_90_h.setFixedHeight(24)
    toolbar.btn_trans_rot_90_h.clicked.connect(toolbar._on_transform_rot_90_clicked)
    l_h.addWidget(toolbar.btn_trans_rot_90_h)

    toolbar.lbl_trans_interp_h = QtWidgets.QLabel("Interp:")
    l_h.addWidget(toolbar.lbl_trans_interp_h)
    toolbar.cbo_trans_interp_h = QtWidgets.QComboBox()
    toolbar.cbo_trans_interp_h.addItems(["Mais Próximo", "Bilinear", "Bicúbica"])
    toolbar.cbo_trans_interp_h.setCurrentIndex(2)
    toolbar.cbo_trans_interp_h.setFixedHeight(24)
    toolbar.cbo_trans_interp_h.currentIndexChanged.connect(lambda idx: toolbar._on_trans_interp_changed(idx, "h"))
    l_h.addWidget(toolbar.cbo_trans_interp_h)

    toolbar.btn_trans_aspect_h = QtWidgets.QToolButton()
    toolbar.btn_trans_aspect_h.setText("Travar Proporção")
    toolbar.btn_trans_aspect_h.setCheckable(True)
    toolbar.btn_trans_aspect_h.setFixedHeight(24)
    toolbar.btn_trans_aspect_h.toggled.connect(lambda v: toolbar._on_trans_aspect_changed(v, "h"))
    l_h.addWidget(toolbar.btn_trans_aspect_h)

    # Vertical
    p_v = QtWidgets.QWidget()
    l_v = QtWidgets.QVBoxLayout(p_v)
    l_v.setContentsMargins(0, 0, 0, 0)
    l_v.setSpacing(6)

    toolbar.lbl_trans_title_v = QtWidgets.QLabel("TRANSFORMAÇÃO")
    toolbar.lbl_trans_title_v.setProperty("heading", "true")
    l_v.addWidget(toolbar.lbl_trans_title_v)

    r1 = QtWidgets.QHBoxLayout()
    toolbar.btn_trans_commit_v = QtWidgets.QToolButton()
    toolbar.btn_trans_commit_v.setObjectName("successButton")
    toolbar.btn_trans_commit_v.setText("Aplicar")
    toolbar.btn_trans_commit_v.setIcon(get_icon("check", ThemeManager.instance().get_color("text_main")))
    toolbar.btn_trans_commit_v.setFixedHeight(24)
    toolbar.btn_trans_commit_v.clicked.connect(toolbar._on_transform_commit_clicked)
    r1.addWidget(toolbar.btn_trans_commit_v)

    toolbar.btn_trans_cancel_v = QtWidgets.QToolButton()
    toolbar.btn_trans_cancel_v.setText("Cancelar")
    toolbar.btn_trans_cancel_v.setIcon(get_icon("close", ThemeManager.instance().get_color("text_main")))
    toolbar.btn_trans_cancel_v.setFixedHeight(24)
    toolbar.btn_trans_cancel_v.clicked.connect(toolbar._on_transform_cancel_clicked)
    r1.addWidget(toolbar.btn_trans_cancel_v)
    l_v.addLayout(r1)

    r2 = QtWidgets.QHBoxLayout()
    toolbar.btn_trans_flip_h_v = QtWidgets.QToolButton()
    toolbar.btn_trans_flip_h_v.setText("Espelhar H")
    toolbar.btn_trans_flip_h_v.setFixedHeight(24)
    toolbar.btn_trans_flip_h_v.clicked.connect(toolbar._on_transform_flip_h_clicked)
    r2.addWidget(toolbar.btn_trans_flip_h_v)

    toolbar.btn_trans_flip_v_v = QtWidgets.QToolButton()
    toolbar.btn_trans_flip_v_v.setText("Espelhar V")
    toolbar.btn_trans_flip_v_v.setFixedHeight(24)
    toolbar.btn_trans_flip_v_v.clicked.connect(toolbar._on_transform_flip_v_clicked)
    r2.addWidget(toolbar.btn_trans_flip_v_v)
    l_v.addLayout(r2)

    r3 = QtWidgets.QHBoxLayout()
    toolbar.btn_trans_rot_90_v = QtWidgets.QToolButton()
    toolbar.btn_trans_rot_90_v.setText("Girar 90°")
    toolbar.btn_trans_rot_90_v.setFixedHeight(24)
    toolbar.btn_trans_rot_90_v.clicked.connect(toolbar._on_transform_rot_90_clicked)
    r3.addWidget(toolbar.btn_trans_rot_90_v)

    toolbar.btn_trans_aspect_v = QtWidgets.QToolButton()
    toolbar.btn_trans_aspect_v.setText("Proporção")
    toolbar.btn_trans_aspect_v.setCheckable(True)
    toolbar.btn_trans_aspect_v.setFixedHeight(24)
    toolbar.btn_trans_aspect_v.toggled.connect(lambda v: toolbar._on_trans_aspect_changed(v, "v"))
    r3.addWidget(toolbar.btn_trans_aspect_v)
    l_v.addLayout(r3)

    toolbar.cbo_trans_interp_v = QtWidgets.QComboBox()
    toolbar.cbo_trans_interp_v.addItems(["Mais Próximo", "Bilinear", "Bicúbica"])
    toolbar.cbo_trans_interp_v.setCurrentIndex(2)
    toolbar.cbo_trans_interp_v.setFixedHeight(24)
    toolbar.cbo_trans_interp_v.currentIndexChanged.connect(lambda idx: toolbar._on_trans_interp_changed(idx, "v"))
    l_v.addWidget(toolbar.cbo_trans_interp_v)

    toolbar.stacked_widget.addWidget(p_h)
    toolbar.stacked_widget.addWidget(p_v)
    toolbar.panels_h["transform"] = p_h
    toolbar.panels_v["transform"] = p_v
