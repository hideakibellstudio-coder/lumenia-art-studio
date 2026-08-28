"""Modify Selection Dialog — Diálogo para Expandir, Contrair e Suavizar Seleção."""

from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


class ModifySelectionDialog(QtWidgets.QDialog):
    """Diálogo para configurar operações morfológicas de seleção (Expandir, Contrair, Feather)."""

    def __init__(self, mode: str = "expand", parent=None):
        super().__init__(parent)
        self.mode = mode.lower()  # "expand", "contract", "feather"
        
        mode_titles = {
            "expand": "Expandir Seleção",
            "contract": "Contrair Seleção",
            "feather": "Suavizar Borda da Seleção (Feather)"
        }
        self.setWindowTitle(mode_titles.get(self.mode, "Modificar Seleção"))
        self.setFixedSize(360, 220)
        self.setModal(True)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Cabeçalho
        header_layout = QtWidgets.QHBoxLayout()
        icon_name = "plus" if self.mode == "expand" else ("transform" if self.mode == "contract" else "blur")
        icon_lbl = QtWidgets.QLabel()
        icon_lbl.setPixmap(get_icon(icon_name).pixmap(22, 22))
        header_layout.addWidget(icon_lbl)

        title_text = {
            "expand": "Expandir Seleção por:",
            "contract": "Contrair Seleção por:",
            "feather": "Raio de Suavização (Feather):"
        }.get(self.mode, "Quantidade:")

        title_lbl = QtWidgets.QLabel(title_text)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Campo numérico e Slider
        ctrl_box = QtWidgets.QHBoxLayout()
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(1, 100)
        self.slider.setValue(5)

        self.spin = QtWidgets.QSpinBox()
        self.spin.setRange(1, 100)
        self.spin.setValue(5)
        self.spin.setSuffix(" px")

        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)

        ctrl_box.addWidget(self.slider, 1)
        ctrl_box.addWidget(self.spin)
        layout.addLayout(ctrl_box)

        # Dica de preview
        tip_text = {
            "expand": "Aumenta o perímetro da seleção para fora.",
            "contract": "Diminui o perímetro da seleção para dentro.",
            "feather": "Cria uma transição suave e gradiente na borda da seleção."
        }.get(self.mode, "")
        tip_lbl = QtWidgets.QLabel(tip_text)
        tip_lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
        layout.addWidget(tip_lbl)

        layout.addStretch()

        # Botões
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_apply = QtWidgets.QPushButton("Aplicar")
        self.btn_apply.setDefault(True)
        self.btn_apply.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        self.btn_apply.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_apply)

        layout.addLayout(btn_box)

    def get_pixels(self) -> int:
        return self.spin.value()

    def _apply_theme(self):
        theme = ThemeManager.instance()
        border = theme.get_color("border", "#2e2e38")
        text = theme.get_color("text_main", "#ffffff")
        self.setStyleSheet(f"""
            QDialog {{ background-color: {theme.get_color("bg_canvas", "#121214")}; color: {text}; }}
            QSpinBox {{ background-color: {theme.get_color("bg_input", "#26262e")}; color: {text}; border: 1px solid {border}; border-radius: 4px; padding: 4px 8px; }}
        """)
