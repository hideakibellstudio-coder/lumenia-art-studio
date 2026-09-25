"""TransformOptionsWidget e SelectionOptionsWidget — páginas do painel de pincel (views do ToolState)."""

from PySide6 import QtWidgets
from ui.infrastructure.i18n import tr
from ui.core.state import ToolState
from .base import ToolHeaderLabel, ModernOptionCheckBox
from .bound_view import ToolOptionsView


class TransformOptionsWidget(ToolOptionsView):
    """Transformação. O combo "Modo" é a combinação de `lock_aspect` e `distort`;
    "Interpolação Bicúbica" liga `interp_mode` 2 (bicúbica) ou 1 (bilinear).
    """

    def __init__(self, tool_state: ToolState, parent=None):
        super().__init__(tool_state, "transform", parent)
        self.setObjectName("TransformOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()
        self.bind()

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
        self.combo_mode.currentIndexChanged.connect(lambda i: self.publish(lock_aspect=i == 1, distort=i == 2))
        row_mode.addWidget(self.lbl_m)
        row_mode.addWidget(self.combo_mode, 1)
        layout.addLayout(row_mode)

        self.chk_bicubic = ModernOptionCheckBox(tr("tools.bicubic_interp", "Interpolação Bicúbica"))
        self.chk_bicubic.toggled.connect(lambda on: self.publish(interp_mode=2 if on else 1))
        layout.addWidget(self.chk_bicubic)

        layout.addStretch()

    def show_options(self, o):
        self.combo_mode.setCurrentIndex(2 if o["distort"] else 1 if o["lock_aspect"] else 0)
        self.chk_bicubic.setChecked(o["interp_mode"] == 2)

    def retranslate_ui(self):
        self.lbl_m.setText(f"{tr('tools.selection_mode', 'Modo')}:")
        self.chk_bicubic.setText(tr("tools.bicubic_interp", "Interpolação Bicúbica"))


class SelectionOptionsWidget(ToolOptionsView):
    """Seleção retangular, elíptica e laço: uma página só; o painel troca a
    ferramenta mostrada com `set_key` ao trocar de ferramenta.
    """

    def __init__(self, tool_state: ToolState, parent=None):
        super().__init__(tool_state, "rect_select", parent)
        self.setObjectName("SelectionOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()
        self.bind()

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
        self.combo_mode.currentIndexChanged.connect(lambda i: self.publish(mode=i))
        row_mode.addWidget(self.lbl_m)
        row_mode.addWidget(self.combo_mode, 1)
        layout.addLayout(row_mode)

        self.chk_aa = ModernOptionCheckBox(tr("tools.anti_alias", "Anti-Aliasing"))
        self.chk_aa.toggled.connect(lambda v: self.publish(aa=v))
        layout.addWidget(self.chk_aa)

        layout.addStretch()

    def show_options(self, o):
        self.combo_mode.setCurrentIndex(o["mode"])
        self.chk_aa.setChecked(o["aa"])

    def retranslate_ui(self):
        self.lbl_m.setText(f"{tr('tools.selection_mode', 'Modo')}:")
        self.chk_aa.setText(tr("tools.anti_alias", "Anti-Aliasing"))
