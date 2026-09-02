"""
filter_card.py — Card Atômico de Apresentação de Filtro.
=========================================================
Componente visual da coluna da esquerda representando um tipo de filtro.
100% conforme à Regra 6 da Constituição ARCcC (zero hardcode de cores hexadecimais).
"""

from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


class FilterCard(QtWidgets.QFrame):
    """Cartão da lista esquerda representando um tipo de filtro."""

    selected = QtCore.Signal(dict)

    def __init__(self, filter_def: dict, is_selected: bool = False, parent=None):
        super().__init__(parent)
        self.filter_def = filter_def
        self.is_selected = is_selected
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self.update_style)
        self.update_style()

    def _build_ui(self) -> None:
        self.setMinimumHeight(64)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Icon
        icon_lbl = QtWidgets.QLabel()
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setScaledContents(True)
        pix = get_icon(self.filter_def.get("icon", "cat_efeitos")).pixmap(32, 32)
        icon_lbl.setPixmap(pix)
        layout.addWidget(icon_lbl)

        # Text Info
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.name_lbl = QtWidgets.QLabel(self.filter_def["name"])
        self.name_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")

        self.desc_lbl = QtWidgets.QLabel(self.filter_def.get("description", ""))
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("font-size: 11px;")

        text_layout.addWidget(self.name_lbl)
        text_layout.addWidget(self.desc_lbl)
        layout.addLayout(text_layout, 1)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        self.update_style()

    def update_style(self) -> None:
        tm = ThemeManager.instance()
        bg_card = tm.get_color("bg_panel")
        bg_hover = tm.get_color("bg_hover")
        accent = tm.get_color("accent")
        border = tm.get_color("border")
        text_main = tm.get_color("text_main")
        text_muted = tm.get_color("text_muted")

        if self.is_selected:
            self.setStyleSheet(f"""
                FilterCard {{
                    background-color: {bg_hover};
                    border: 1.5px solid {accent};
                    border-radius: 6px;
                }}
            """)
            self.name_lbl.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {accent};")
            self.desc_lbl.setStyleSheet(f"font-size: 11px; color: {text_main};")
        else:
            self.setStyleSheet(f"""
                FilterCard {{
                    background-color: {bg_card};
                    border: 1px solid {border};
                    border-radius: 6px;
                }}
                FilterCard:hover {{
                    background-color: {bg_hover};
                    border: 1px solid {accent};
                }}
            """)
            self.name_lbl.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {text_main};")
            self.desc_lbl.setStyleSheet(f"font-size: 11px; color: {text_muted};")

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.selected.emit(self.filter_def)
        super().mousePressEvent(event)
