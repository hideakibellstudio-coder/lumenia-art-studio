"""BucketOptionsWidget e WandOptionsWidget — páginas do painel de pincel (views do ToolState)."""

from PySide6 import QtCore, QtWidgets
from ui.core.i18n import tr
from ui.core.state import ToolState
from .base import ToolHeaderLabel, ModernOptionCheckBox
from .bound_view import ToolOptionsView


class BucketOptionsWidget(ToolOptionsView):
    """Painel de configurações da ferramenta Balde de Tinta (Fit Compacto e Rico)."""

    def __init__(self, tool_state: ToolState, parent=None):
        super().__init__(tool_state, "bucket", parent)
        self.setObjectName("BucketOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()
        self.bind()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel(tr("tools.fill", "Balde de Tinta"), icon_name="bucket"))

        tol_layout = QtWidgets.QHBoxLayout()
        tol_layout.setContentsMargins(0, 0, 0, 0)
        tol_layout.setSpacing(4)
        self.lbl_t = QtWidgets.QLabel(f"{tr('tools.tolerance', 'Tol')}:")
        self.lbl_t.setProperty("muted", "true")
        self.slider_tol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_tol.setRange(0, 100)
        self.slider_tol.setFixedHeight(18)
        self.lbl_tol_val = QtWidgets.QLabel("20%")
        self.lbl_tol_val.setFixedWidth(28)
        self.lbl_tol_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_tol_val.setProperty("heading", "true")
        self.slider_tol.valueChanged.connect(lambda v: self.publish(tolerance=v))

        tol_layout.addWidget(self.lbl_t)
        tol_layout.addWidget(self.slider_tol, 1)
        tol_layout.addWidget(self.lbl_tol_val)
        layout.addLayout(tol_layout)

        exp_layout = QtWidgets.QHBoxLayout()
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.setSpacing(4)
        self.lbl_e = QtWidgets.QLabel(f"{tr('tools.expansion', 'Exp')}:")
        self.lbl_e.setToolTip(tr("tools.expansion_tooltip", "Expande o preenchimento sob o traço para evitar halos e linhas brancas"))
        self.lbl_e.setProperty("muted", "true")
        self.slider_exp = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_exp.setRange(-10, 10)
        self.slider_exp.setFixedHeight(18)
        self.lbl_exp_val = QtWidgets.QLabel("+1px")
        self.lbl_exp_val.setFixedWidth(28)
        self.lbl_exp_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_exp_val.setProperty("heading", "true")
        self.lbl_exp_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        self.slider_exp.valueChanged.connect(lambda v: self.publish(expand_px=v))

        exp_layout.addWidget(self.lbl_e)
        exp_layout.addWidget(self.slider_exp, 1)
        exp_layout.addWidget(self.lbl_exp_val)
        layout.addLayout(exp_layout)

        self.chk_contiguous = ModernOptionCheckBox(tr("tools.contiguous", "Contíguo"))
        self.chk_contiguous.setToolTip(tr("tools.contiguous_tooltip", "Preenche apenas pixels conectados e adjacentes"))
        self.chk_contiguous.toggled.connect(lambda v: self.publish(contiguous=v))
        layout.addWidget(self.chk_contiguous)

        self.chk_sample_all = ModernOptionCheckBox(tr("tools.sample_all_layers", "Todas as Camadas"))
        self.chk_sample_all.setToolTip(tr("tools.sample_all_tooltip", "Detecta limites considerando todas as camadas visíveis"))
        self.chk_sample_all.toggled.connect(lambda v: self.publish(sample_all=v))
        layout.addWidget(self.chk_sample_all)

        layout.addStretch()

    def show_options(self, o):
        self.slider_tol.setValue(o["tolerance"])
        self.lbl_tol_val.setText(f"{o['tolerance']}%")
        self.slider_exp.setValue(o["expand_px"])
        self.lbl_exp_val.setText(f"{o['expand_px']:+d}px" if o["expand_px"] else "0px")
        self.chk_contiguous.setChecked(o["contiguous"])
        self.chk_sample_all.setChecked(o["sample_all"])

    def retranslate_ui(self):
        self.lbl_t.setText(f"{tr('tools.tolerance', 'Tol')}:")
        self.lbl_e.setText(f"{tr('tools.expansion', 'Exp')}:")
        self.lbl_e.setToolTip(tr("tools.expansion_tooltip", "Expande o preenchimento sob o traço para evitar halos e linhas brancas"))
        self.chk_contiguous.setText(tr("tools.contiguous", "Contíguo"))
        self.chk_contiguous.setToolTip(tr("tools.contiguous_tooltip", "Preenche apenas pixels conectados e adjacentes"))
        self.chk_sample_all.setText(tr("tools.sample_all_layers", "Todas as Camadas"))
        self.chk_sample_all.setToolTip(tr("tools.sample_all_tooltip", "Detecta limites considerando todas as camadas visíveis"))


class WandOptionsWidget(ToolOptionsView):
    """Painel de configurações da Varinha Mágica (Fit Compacto)."""

    def __init__(self, tool_state: ToolState, parent=None):
        super().__init__(tool_state, "wand", parent)
        self.setObjectName("WandOptionsWidget")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self._build_ui()
        self.bind()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(ToolHeaderLabel(tr("tools.wand", "Varinha Mágica"), icon_name="wand"))

        tol_layout = QtWidgets.QHBoxLayout()
        tol_layout.setContentsMargins(0, 0, 0, 0)
        tol_layout.setSpacing(4)
        self.lbl_t = QtWidgets.QLabel(f"{tr('tools.tolerance', 'Tol')}:")
        self.lbl_t.setProperty("muted", "true")
        self.slider_tol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_tol.setRange(0, 100)
        self.slider_tol.setFixedHeight(18)
        self.lbl_tol_val = QtWidgets.QLabel("20%")
        self.lbl_tol_val.setFixedWidth(28)
        self.lbl_tol_val.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lbl_tol_val.setProperty("heading", "true")
        self.slider_tol.valueChanged.connect(lambda v: self.publish(tolerance=v))

        tol_layout.addWidget(self.lbl_t)
        tol_layout.addWidget(self.slider_tol, 1)
        tol_layout.addWidget(self.lbl_tol_val)
        layout.addLayout(tol_layout)

        self.chk_contiguous = ModernOptionCheckBox(tr("tools.contiguous", "Contíguo"))
        self.chk_contiguous.toggled.connect(lambda v: self.publish(contiguous=v))
        layout.addWidget(self.chk_contiguous)

        self.chk_sample_all = ModernOptionCheckBox(tr("tools.sample_all_layers", "Todas as Camadas"))
        self.chk_sample_all.toggled.connect(lambda v: self.publish(sample_all=v))
        layout.addWidget(self.chk_sample_all)

        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(4)
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
        mode_layout.addWidget(self.lbl_m)
        mode_layout.addWidget(self.combo_mode, 1)
        layout.addLayout(mode_layout)

        layout.addStretch()

    def show_options(self, o):
        self.slider_tol.setValue(o["tolerance"])
        self.lbl_tol_val.setText(f"{o['tolerance']}%")
        self.chk_contiguous.setChecked(o["contiguous"])
        self.chk_sample_all.setChecked(o["sample_all"])
        self.combo_mode.setCurrentIndex(o["mode"])

    def retranslate_ui(self):
        self.lbl_t.setText(f"{tr('tools.tolerance', 'Tol')}:")
        self.lbl_m.setText(f"{tr('tools.selection_mode', 'Modo')}:")
        self.chk_contiguous.setText(tr("tools.contiguous", "Contíguo"))
        self.chk_sample_all.setText(tr("tools.sample_all_layers", "Todas as Camadas"))
