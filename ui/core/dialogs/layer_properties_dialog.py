"""Layer Properties Dialog — Diálogo de Propriedades e Ajuste da Camada."""

from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.i18n import tr


def get_blend_modes() -> list[tuple[int, str]]:
    return [
        (0, tr("blend_mode.normal", "Normal")),
        (1, tr("blend_mode.multiply", "Multiplicação (Multiply)")),
        (2, tr("blend_mode.screen", "Divisão / Tela (Screen)")),
        (3, tr("blend_mode.overlay", "Sobreposição (Overlay)")),
        (4, tr("blend_mode.darken", "Escurecer (Darken)")),
        (5, tr("blend_mode.lighten", "Clarear (Lighten)")),
        (6, tr("blend_mode.additive", "Adicionar / Luz Linear (Additive)")),
        (7, tr("blend_mode.erase", "Borracha / Limpar (Erase)")),
    ]


class LayerPropertiesDialog(BaseFramelessDialog):
    """Diálogo modal para editar nome, opacidade e modo de mesclagem da camada ativa."""

    def __init__(self, name: str, opacity: float = 1.0, blend_mode: int = 0, is_visible: bool = True,
                 is_alpha_locked: bool = False, is_clipping: bool = False, parent=None):
        super().__init__(title=tr("dialogs.layer_properties_title", "Propriedades da Camada"), icon_name="layers", parent=parent, modal=True)
        self.resize(400, 370)

        self._name = name
        self._opacity = int(round(opacity * 100)) if opacity <= 1.0 else int(opacity)
        self._blend_mode = blend_mode
        self._is_visible = is_visible
        self._is_alpha_locked = is_alpha_locked
        self._is_clipping = is_clipping

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self):
        # Formulário
        form_layout = QtWidgets.QGridLayout()
        form_layout.setSpacing(10)

        # Nome
        form_layout.addWidget(QtWidgets.QLabel(f"{tr('dialogs.layer_name', 'Nome da Camada')}:"), 0, 0)
        self.name_edit = QtWidgets.QLineEdit(self._name)
        form_layout.addWidget(self.name_edit, 0, 1)

        # Opacidade
        form_layout.addWidget(QtWidgets.QLabel(f"{tr('layers.opacity', 'Opacidade')}:"), 1, 0)
        op_box = QtWidgets.QHBoxLayout()
        self.op_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.op_slider.setRange(0, 100)
        self.op_slider.setValue(self._opacity)

        self.op_spin = QtWidgets.QSpinBox()
        self.op_spin.setRange(0, 100)
        self.op_spin.setValue(self._opacity)
        self.op_spin.setSuffix("%")

        self.op_slider.valueChanged.connect(self.op_spin.setValue)
        self.op_spin.valueChanged.connect(self.op_slider.setValue)

        op_box.addWidget(self.op_slider, 1)
        op_box.addWidget(self.op_spin)
        form_layout.addLayout(op_box, 1, 1)

        # Modo de Mesclagem
        form_layout.addWidget(QtWidgets.QLabel(f"{tr('layers.blend_mode', 'Modo de Mesclagem')}:"), 2, 0)
        self.blend_combo = QtWidgets.QComboBox()
        for mode_id, mode_label in get_blend_modes():
            self.blend_combo.addItem(mode_label, mode_id)
            if mode_id == self._blend_mode:
                self.blend_combo.setCurrentIndex(self.blend_combo.count() - 1)
        form_layout.addWidget(self.blend_combo, 2, 1)

        self.content_layout.addLayout(form_layout)

        # Travas e Modificadores
        box_mod = QtWidgets.QGroupBox(tr("dialogs.layer_modifiers", "Modificadores Rápidos"))
        box_mod_layout = QtWidgets.QVBoxLayout(box_mod)
        self.check_vis = QtWidgets.QCheckBox(tr("dialogs.layer_visible", "Camada Visível"))
        self.check_vis.setChecked(self._is_visible)
        box_mod_layout.addWidget(self.check_vis)

        self.check_alock = QtWidgets.QCheckBox(tr("layers.alpha_lock", "Bloquear Transparência (Alpha Lock)"))
        self.check_alock.setChecked(self._is_alpha_locked)
        box_mod_layout.addWidget(self.check_alock)

        self.check_clip = QtWidgets.QCheckBox(tr("layers.clipping_mask", "Máscara de Corte (Clipping Mask)"))
        self.check_clip.setChecked(self._is_clipping)
        box_mod_layout.addWidget(self.check_clip)
        self.content_layout.addWidget(box_mod)

        self.content_layout.addStretch()

        # Botões
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QtWidgets.QPushButton(tr("dialogs.cancel", "Cancelar"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_ok = QtWidgets.QPushButton(tr("dialogs.apply", "Aplicar"))
        self.btn_ok.setDefault(True)
        self.btn_ok.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        self.btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_ok)

        self.content_layout.addLayout(btn_box)

    def get_results(self) -> dict:
        return {
            "name": self.name_edit.text().strip() or "Camada",
            "opacity": self.op_spin.value() / 100.0,
            "blend_mode": self.blend_combo.currentData(),
            "is_visible": self.check_vis.isChecked(),
            "is_alpha_locked": self.check_alock.isChecked(),
            "is_clipping": self.check_clip.isChecked()
        }

    def _apply_theme(self, *args):
        theme = ThemeManager.instance()
        border = theme.get_color("border", "#2e2e38")
        text = theme.get_color("text_main", "#ffffff")
        self.setStyleSheet(f"""
            QLineEdit, QSpinBox, QComboBox {{ background-color: {theme.get_color("bg_input", "#26262e")}; color: {text}; border: 1px solid {border}; border-radius: 4px; padding: 4px 8px; }}
            QGroupBox {{ border: 1px solid {border}; border-radius: 6px; margin-top: 6px; padding-top: 10px; }}
        """)
