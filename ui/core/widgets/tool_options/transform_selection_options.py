"""TransformOptionsWidget and SelectionOptionsWidget."""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.i18n import tr, I18nManager
from .base import ToolHeaderLabel, ModernOptionCheckBox


class TransformOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações da ferramenta Transformação (Fit Compacto)."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TransformOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel(tr("tools.transform", "Transformar"), icon_name="transform"))

        row_mode = QtWidgets.QHBoxLayout()
        row_mode.setContentsMargins(0, 0, 0, 0)
        row_mode.setSpacing(4)
        self.lbl_m = QtWidgets.QLabel(f"{tr('tools.selection_mode', 'Modo')}:")
        self.lbl_m.setProperty("muted", "true")
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems([
            tr("tools.transform_free", "Livre"),
            tr("tools.transform_proportional", "Proporcional"),
            tr("tools.transform_distort", "Distorcer")
        ])
        self.combo_mode.setFixedHeight(22)
        row_mode.addWidget(self.lbl_m)
        row_mode.addWidget(self.combo_mode, 1)
        layout.addLayout(row_mode)

        self.chk_bicubic = ModernOptionCheckBox(tr("tools.bicubic_interp", "Interpolação Bicúbica"))
        self.chk_bicubic.setChecked(True)
        layout.addWidget(self.chk_bicubic)

        layout.addStretch()

    def retranslate_ui(self):
        if hasattr(self, "lbl_m"):
            self.lbl_m.setText(f"{tr('tools.selection_mode', 'Modo')}:")
        if hasattr(self, "chk_bicubic"):
            self.chk_bicubic.setText(tr("tools.bicubic_interp", "Interpolação Bicúbica"))


class SelectionOptionsWidget(QtWidgets.QWidget):
    """Painel de configurações das ferramentas de Seleção (Fit Compacto)."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SelectionOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel(tr("menu.select.title", "Seleção"), icon_name="select_rect"))

        row_mode = QtWidgets.QHBoxLayout()
        row_mode.setContentsMargins(0, 0, 0, 0)
        row_mode.setSpacing(4)
        self.lbl_m = QtWidgets.QLabel(f"{tr('tools.selection_mode', 'Modo')}:")
        self.lbl_m.setProperty("muted", "true")
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems([
            tr("tools.mode_new", "Nova"),
            tr("tools.mode_add", "Adicionar (+)"),
            tr("tools.mode_sub", "Subtrair (-)"),
            tr("tools.mode_intersect", "Interseção")
        ])
        self.combo_mode.setFixedHeight(22)
        row_mode.addWidget(self.lbl_m)
        row_mode.addWidget(self.combo_mode, 1)
        layout.addLayout(row_mode)

        self.chk_aa = ModernOptionCheckBox(tr("tools.anti_alias", "Anti-Aliasing"))
        self.chk_aa.setChecked(True)
        layout.addWidget(self.chk_aa)

        layout.addStretch()

    def retranslate_ui(self):
        if hasattr(self, "lbl_m"):
            self.lbl_m.setText(f"{tr('tools.selection_mode', 'Modo')}:")
        if hasattr(self, "chk_aa"):
            self.chk_aa.setText(tr("tools.anti_alias", "Anti-Aliasing"))
