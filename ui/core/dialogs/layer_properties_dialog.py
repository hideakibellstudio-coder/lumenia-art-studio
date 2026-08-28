"""Layer Properties Dialog — Diálogo de Propriedades e Ajuste da Camada."""

from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


BLEND_MODES = [
    (0, "Normal"),
    (1, "Multiplicação (Multiply)"),
    (2, "Divisão / Tela (Screen)"),
    (3, "Sobreposição (Overlay)"),
    (4, "Escurecer (Darken)"),
    (5, "Clarear (Lighten)"),
    (6, "Adicionar / Luz Linear (Additive)"),
    (7, "Borracha / Limpar (Erase)"),
]


class LayerPropertiesDialog(QtWidgets.QDialog):
    """Diálogo modal para editar nome, opacidade e modo de mesclagem da camada ativa."""

    def __init__(self, name: str, opacity: float = 1.0, blend_mode: int = 0, is_visible: bool = True,
                 is_alpha_locked: bool = False, is_clipping: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Propriedades da Camada")
        self.setFixedSize(380, 360)
        self.setModal(True)

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
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Cabeçalho
        header = QtWidgets.QHBoxLayout()
        icon_lbl = QtWidgets.QLabel()
        icon_lbl.setPixmap(get_icon("layers").pixmap(24, 24))
        header.addWidget(icon_lbl)

        title_lbl = QtWidgets.QLabel("Configurações da Camada")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        # Formulário
        form_layout = QtWidgets.QGridLayout()
        form_layout.setSpacing(10)

        # Nome
        form_layout.addWidget(QtWidgets.QLabel("Nome da Camada:"), 0, 0)
        self.name_edit = QtWidgets.QLineEdit(self._name)
        form_layout.addWidget(self.name_edit, 0, 1)

        # Opacidade
        form_layout.addWidget(QtWidgets.QLabel("Opacidade:"), 1, 0)
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
        form_layout.addWidget(QtWidgets.QLabel("Modo de Mesclagem:"), 2, 0)
        self.blend_combo = QtWidgets.QComboBox()
        for mode_id, mode_label in BLEND_MODES:
            self.blend_combo.addItem(mode_label, mode_id)
            if mode_id == self._blend_mode:
                self.blend_combo.setCurrentIndex(self.blend_combo.count() - 1)
        form_layout.addWidget(self.blend_combo, 2, 1)

        layout.addLayout(form_layout)

        # Travas e Modificadores
        box_mod = QtWidgets.QGroupBox("Modificadores Rápidos")
        box_mod_layout = QtWidgets.QVBoxLayout(box_mod)
        self.check_vis = QtWidgets.QCheckBox("Camada Visível")
        self.check_vis.setChecked(self._is_visible)
        box_mod_layout.addWidget(self.check_vis)

        self.check_alock = QtWidgets.QCheckBox("Bloquear Transparência (Alpha Lock)")
        self.check_alock.setChecked(self._is_alpha_locked)
        box_mod_layout.addWidget(self.check_alock)

        self.check_clip = QtWidgets.QCheckBox("Máscara de Corte (Clipping Mask)")
        self.check_clip.setChecked(self._is_clipping)
        box_mod_layout.addWidget(self.check_clip)
        layout.addWidget(box_mod)

        layout.addStretch()

        # Botões
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_apply = QtWidgets.QPushButton("Salvar Alterações")
        self.btn_apply.setDefault(True)
        self.btn_apply.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        self.btn_apply.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_apply)

        layout.addLayout(btn_box)

    def get_results(self) -> dict:
        return {
            "name": self.name_edit.text().strip() or "Camada",
            "opacity": self.op_spin.value() / 100.0,
            "blend_mode": self.blend_combo.currentData(),
            "is_visible": self.check_vis.isChecked(),
            "is_alpha_locked": self.check_alock.isChecked(),
            "is_clipping": self.check_clip.isChecked()
        }

    def _apply_theme(self):
        theme = ThemeManager.instance()
        border = theme.get_color("border", "#2e2e38")
        text = theme.get_color("text_main", "#ffffff")
        self.setStyleSheet(f"""
            QDialog {{ background-color: {theme.get_color("bg_canvas", "#121214")}; color: {text}; }}
            QLineEdit, QSpinBox, QComboBox {{ background-color: {theme.get_color("bg_input", "#26262e")}; color: {text}; border: 1px solid {border}; border-radius: 4px; padding: 4px 8px; }}
            QGroupBox {{ border: 1px solid {border}; border-radius: 6px; margin-top: 6px; padding-top: 10px; }}
        """)
