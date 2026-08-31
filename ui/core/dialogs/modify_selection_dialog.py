"""Modify Selection Dialog — Diálogo para Expandir, Contrair e Suavizar Seleção (ARCcC i18n)."""

from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.i18n import tr


class ModifySelectionDialog(BaseFramelessDialog):
    """Diálogo para configurar operações morfológicas de seleção (Expandir, Contrair, Feather)."""

    def __init__(self, mode: str = "expand", parent=None):
        self.mode = mode.lower()  # "expand", "contract", "feather"
        mode_titles = {
            "expand": tr("menu.select.expand", "Expandir Seleção"),
            "contract": tr("menu.select.contract", "Contrair Seleção"),
            "feather": tr("menu.select.feather", "Suavizar Borda (Feather)")
        }
        icon_name = "plus" if self.mode == "expand" else ("transform" if self.mode == "contract" else "blur")
        title = mode_titles.get(self.mode, tr("menu.select.modify_menu", "Modificar Seleção"))

        super().__init__(title=title, icon_name=icon_name, parent=parent, modal=True)
        self.resize(380, 240)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self):
        title_text = {
            "expand": f"{tr('menu.select.expand', 'Expandir Seleção')} por:",
            "contract": f"{tr('menu.select.contract', 'Contrair Seleção')} por:",
            "feather": f"{tr('dialogs.feather_radius', 'Raio de Suavização (Feather)')}:"
        }.get(self.mode, f"{tr('dialogs.amount', 'Quantidade')}:")

        title_lbl = QtWidgets.QLabel(title_text)
        title_lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.content_layout.addWidget(title_lbl)

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
        self.content_layout.addLayout(ctrl_box)

        # Dica de preview
        tip_text = {
            "expand": tr("dialogs.expand_tip", "Aumenta o perímetro da seleção para fora."),
            "contract": tr("dialogs.contract_tip", "Diminui o perímetro da seleção para dentro."),
            "feather": tr("dialogs.feather_tip", "Cria uma transição suave e gradiente na borda da seleção.")
        }.get(self.mode, "")
        tip_lbl = QtWidgets.QLabel(tip_text)
        tip_lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
        self.content_layout.addWidget(tip_lbl)

        self.content_layout.addStretch()

        # Botões
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QtWidgets.QPushButton(tr("dialogs.cancel", "Cancelar"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_apply = QtWidgets.QPushButton(tr("dialogs.apply", "Aplicar"))
        self.btn_apply.setDefault(True)
        self.btn_apply.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        self.btn_apply.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_apply)

        self.content_layout.addLayout(btn_box)

    def get_pixels(self) -> int:
        return self.spin.value()

    def _apply_theme(self, *args):
        theme = ThemeManager.instance()
        border = theme.get_color("border", "#2e2e38")
        text = theme.get_color("text_main", "#ffffff")
        self.setStyleSheet(f"""
            QSpinBox {{ background-color: {theme.get_color("bg_input", "#26262e")}; color: {text}; border: 1px solid {border}; border-radius: 4px; padding: 4px 8px; }}
        """)
