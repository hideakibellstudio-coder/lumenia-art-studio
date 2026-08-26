"""BucketOptionsWidget and WandOptionsWidget."""

from PySide6 import QtCore, QtGui, QtWidgets
from .base import ToolHeaderLabel, ModernOptionCheckBox


class BucketOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações da ferramenta Balde de Tinta (Fit Compacto e Rico)."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BucketOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel("Balde de Tinta", icon_name="bucket"))

        tol_layout = QtWidgets.QHBoxLayout()
        tol_layout.setContentsMargins(0, 0, 0, 0)
        tol_layout.setSpacing(4)
        lbl_t = QtWidgets.QLabel("Tol:")
        lbl_t.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.slider_tol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_tol.setRange(0, 100)
        self.slider_tol.setValue(20)
        self.slider_tol.setFixedHeight(18)
        self.lbl_tol_val = QtWidgets.QLabel("20%")
        self.lbl_tol_val.setFixedWidth(28)
        self.lbl_tol_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_tol_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_tol.valueChanged.connect(lambda v: self.lbl_tol_val.setText(f"{v}%"))
        self.slider_tol.valueChanged.connect(self._emit_changes)

        tol_layout.addWidget(lbl_t)
        tol_layout.addWidget(self.slider_tol, 1)
        tol_layout.addWidget(self.lbl_tol_val)
        layout.addLayout(tol_layout)

        exp_layout = QtWidgets.QHBoxLayout()
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.setSpacing(4)
        lbl_e = QtWidgets.QLabel("Exp:")
        lbl_e.setToolTip("Expande o preenchimento sob o traço para evitar halos e linhas brancas")
        lbl_e.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.slider_exp = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_exp.setRange(-10, 10)
        self.slider_exp.setValue(1)
        self.slider_exp.setFixedHeight(18)
        self.lbl_exp_val = QtWidgets.QLabel("+1px")
        self.lbl_exp_val.setFixedWidth(28)
        self.lbl_exp_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_exp_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_exp.valueChanged.connect(lambda v: self.lbl_exp_val.setText(f"{v:+d}px" if v != 0 else "0px"))
        self.slider_exp.valueChanged.connect(self._emit_changes)

        exp_layout.addWidget(lbl_e)
        exp_layout.addWidget(self.slider_exp, 1)
        exp_layout.addWidget(self.lbl_exp_val)
        layout.addLayout(exp_layout)

        gap_layout = QtWidgets.QHBoxLayout()
        gap_layout.setContentsMargins(0, 0, 0, 0)
        gap_layout.setSpacing(4)
        lbl_g = QtWidgets.QLabel("Gap:")
        lbl_g.setToolTip("Fecha furos e aberturas no traço para evitar que a tinta vase para fora")
        lbl_g.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.slider_gap = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_gap.setRange(0, 5)
        self.slider_gap.setValue(0)
        self.slider_gap.setFixedHeight(18)
        self.lbl_gap_val = QtWidgets.QLabel("0px")
        self.lbl_gap_val.setFixedWidth(28)
        self.lbl_gap_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_gap_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_gap.valueChanged.connect(lambda v: self.lbl_gap_val.setText(f"{v}px"))
        self.slider_gap.valueChanged.connect(self._emit_changes)

        gap_layout.addWidget(lbl_g)
        gap_layout.addWidget(self.slider_gap, 1)
        gap_layout.addWidget(self.lbl_gap_val)
        layout.addLayout(gap_layout)

        layout.addSpacing(2)

        self.chk_contiguous = ModernOptionCheckBox("Contíguo (Conectado)")
        self.chk_contiguous.setChecked(True)
        self.chk_contiguous.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_contiguous)

        self.chk_aa = ModernOptionCheckBox("Anti-Aliasing Suave")
        self.chk_aa.setChecked(True)
        self.chk_aa.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_aa)

        self.chk_sample_all = ModernOptionCheckBox("Todas as Camadas")
        self.chk_sample_all.setToolTip("Preencher considerando a imagem mesclada ou apenas a camada atual")
        self.chk_sample_all.setChecked(True)
        self.chk_sample_all.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_sample_all)

        layout.addStretch()

    def get_settings(self) -> dict:
        return {
            "tolerance": self.slider_tol.value(),
            "expand_px": self.slider_exp.value(),
            "gap_closing_px": self.slider_gap.value(),
            "contiguous": self.chk_contiguous.isChecked(),
            "aa": self.chk_aa.isChecked(),
            "sample_all": self.chk_sample_all.isChecked(),
        }

    def _emit_changes(self):
        self.settingsChanged.emit(self.get_settings())


class WandOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações da ferramenta Varinha Mágica (Fit Compacto)."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WandOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel("Varinha Mágica", icon_name="wand"))

        tol_layout = QtWidgets.QHBoxLayout()
        tol_layout.setContentsMargins(0, 0, 0, 0)
        tol_layout.setSpacing(4)
        lbl_t = QtWidgets.QLabel("Tol:")
        lbl_t.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.slider_tol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_tol.setRange(0, 100)
        self.slider_tol.setValue(32)
        self.slider_tol.setFixedHeight(18)
        self.lbl_tol_val = QtWidgets.QLabel("32%")
        self.lbl_tol_val.setFixedWidth(28)
        self.lbl_tol_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_tol_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_tol.valueChanged.connect(lambda v: self.lbl_tol_val.setText(f"{v}%"))
        self.slider_tol.valueChanged.connect(self._emit_changes)

        tol_layout.addWidget(lbl_t)
        tol_layout.addWidget(self.slider_tol, 1)
        tol_layout.addWidget(self.lbl_tol_val)
        layout.addLayout(tol_layout)

        self.chk_contiguous = ModernOptionCheckBox("Contíguo")
        self.chk_contiguous.setChecked(True)
        self.chk_contiguous.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_contiguous)

        self.chk_sample_all = ModernOptionCheckBox("Todas as Camadas")
        self.chk_sample_all.setChecked(True)
        self.chk_sample_all.toggled.connect(self._emit_changes)
        layout.addWidget(self.chk_sample_all)

        layout.addStretch()

    def get_settings(self) -> dict:
        return {
            "tolerance": self.slider_tol.value(),
            "contiguous": self.chk_contiguous.isChecked(),
            "sample_all": self.chk_sample_all.isChecked(),
        }

    def _emit_changes(self):
        self.settingsChanged.emit(self.get_settings())
