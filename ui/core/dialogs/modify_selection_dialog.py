"""Modify Selection Dialog — Diálogo para Expandir, Contrair e Suavizar Seleção (ARCcC i18n)."""

from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets
from ui.infrastructure.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.infrastructure.i18n import tr


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

        from ui.infrastructure.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def _build_ui(self):
        self.title_lbl = QtWidgets.QLabel()
        self.title_lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.content_layout.addWidget(self.title_lbl)

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
        self.tip_lbl = QtWidgets.QLabel()
        self.tip_lbl.setProperty("muted", "true")
        self.content_layout.addWidget(self.tip_lbl)

        self.content_layout.addStretch()

        # Botões
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QtWidgets.QPushButton(tr("dialogs.cancel", "Cancelar"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_apply = QtWidgets.QPushButton(tr("dialogs.apply", "Aplicar"))
        self.btn_apply.setObjectName("accentButton")
        self.btn_apply.setDefault(True)
        self.btn_apply.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_apply)

        self.content_layout.addLayout(btn_box)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        mode_titles = {
            "expand": tr("menu.select.expand", "Expandir Seleção"),
            "contract": tr("menu.select.contract", "Contrair Seleção"),
            "feather": tr("menu.select.feather", "Suavizar Borda (Feather)")
        }
        title = mode_titles.get(self.mode, tr("menu.select.modify_menu", "Modificar Seleção"))
        self.setWindowTitle(title)
        if hasattr(self, "title_bar") and self.title_bar:
            self.title_bar.set_title(title)

        title_text = {
            "expand": f"{tr('menu.select.expand', 'Expandir Seleção')} por:",
            "contract": f"{tr('menu.select.contract', 'Contrair Seleção')} por:",
            "feather": f"{tr('dialogs.feather_radius', 'Raio de Suavização (Feather)')}:"
        }.get(self.mode, f"{tr('dialogs.amount', 'Quantidade')}:")
        if hasattr(self, "title_lbl"):
            self.title_lbl.setText(title_text)

        tip_text = {
            "expand": tr("dialogs.expand_tip", "Aumenta o perímetro da seleção para fora."),
            "contract": tr("dialogs.contract_tip", "Diminui o perímetro da seleção para dentro."),
            "feather": tr("dialogs.feather_tip", "Cria uma transição suave e gradiente na borda da seleção.")
        }.get(self.mode, "")
        if hasattr(self, "tip_lbl"):
            self.tip_lbl.setText(tip_text)

        if hasattr(self, "btn_cancel"):
            self.btn_cancel.setText(tr("dialogs.cancel", "Cancelar"))
        if hasattr(self, "btn_apply"):
            self.btn_apply.setText(tr("dialogs.apply", "Aplicar"))

    def get_pixels(self) -> int:
        return self.spin.value()

    def _apply_theme(self, *args):
        theme = ThemeManager.instance()
        border = theme.get_color("border", "#2e2e38")
        text = theme.get_color("text_main", "#ffffff")
        self.setStyleSheet(f"""
            QSpinBox {{ background-color: {theme.get_color("bg_input", "#26262e")}; color: {text}; border: 1px solid {border}; border-radius: 4px; padding: 4px 8px; }}
        """)
