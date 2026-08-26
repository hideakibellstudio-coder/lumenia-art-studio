"""TransformOptionsWidget and SelectionOptionsWidget."""

from PySide6 import QtCore, QtGui, QtWidgets
from .base import ToolHeaderLabel, ModernOptionCheckBox


class TransformOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações da ferramenta Transformação (Fit Compacto)."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TransformOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel("Transformar", icon_name="transform"))

        row_mode = QtWidgets.QHBoxLayout()
        row_mode.setContentsMargins(0, 0, 0, 0)
        row_mode.setSpacing(4)
        lbl_m = QtWidgets.QLabel("Modo:")
        lbl_m.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems(["Livre", "Proporcional", "Distorcer"])
        self.combo_mode.setFixedHeight(22)
        self.combo_mode.setStyleSheet("font-size: 10px; padding: 1px 4px;")
        row_mode.addWidget(lbl_m)
        row_mode.addWidget(self.combo_mode, 1)
        layout.addLayout(row_mode)

        self.chk_bicubic = ModernOptionCheckBox("Interpolação Bicúbica")
        self.chk_bicubic.setChecked(True)
        layout.addWidget(self.chk_bicubic)

        layout.addStretch()


class SelectionOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações das ferramentas de Seleção (Fit Compacto)."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SelectionOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel("Seleção", icon_name="select_rect"))

        row_mode = QtWidgets.QHBoxLayout()
        row_mode.setContentsMargins(0, 0, 0, 0)
        row_mode.setSpacing(4)
        lbl_m = QtWidgets.QLabel("Modo:")
        lbl_m.setStyleSheet("font-size: 10px; color: #a1a1aa;")
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems(["Nova", "Adicionar (+)", "Subtrair (-)", "Interseção (∩)"])
        self.combo_mode.setFixedHeight(22)
        self.combo_mode.setStyleSheet("font-size: 10px; padding: 1px 4px;")
        row_mode.addWidget(lbl_m)
        row_mode.addWidget(self.combo_mode, 1)
        layout.addLayout(row_mode)

        self.chk_aa = ModernOptionCheckBox("Anti-Aliasing")
        self.chk_aa.setChecked(True)
        layout.addWidget(self.chk_aa)

        layout.addStretch()
