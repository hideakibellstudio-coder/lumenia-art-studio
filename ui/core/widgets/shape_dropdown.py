"""
ui.core.widgets.shape_dropdown — Dropdown Personalizado em Grid para Formas Vetoriais
====================================================================================
Apresenta a seleção de formas vetoriais (Linha, Retângulo, Elipse, Polígono, Estrela)
em um grid popover elegante com ícones SVG e temas dinâmicos, sem poluir a barra lateral.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.icons import get_icon
from ui.core.theme.manager import ThemeManager

SHAPE_ITEMS = [
    {"id": "shape_line", "label": "Linha Reta", "icon": "shape_line", "tooltip": "Linha Reta (Shift: Trava Ângulo)"},
    {"id": "shape_rect", "label": "Retângulo", "icon": "shape_rect", "tooltip": "Retângulo / Quadrado (Shift: 1:1)"},
    {"id": "shape_ellipse", "label": "Elipse", "icon": "shape_ellipse", "tooltip": "Elipse / Círculo (Shift: 1:1)"},
    {"id": "shape_polygon", "label": "Polígono", "icon": "shape_polygon", "tooltip": "Polígono Regular (3 a 16 lados)"},
    {"id": "shape_star", "label": "Estrela", "icon": "shape_star", "tooltip": "Estrela Paramétrica (3 a 16 pontas)"},
]


class ShapeSelectorPopup(QtWidgets.QDialog):
    """
    Popup flutuante de seleção de Formas Vetoriais contendo um grid elegante
    de botões com ícones SVG e temas dinâmicos.
    """

    shape_selected = QtCore.Signal(str, str)  # (shape_id, shape_label)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        flags = QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint
        super().__init__(parent, flags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("QDialog { background: transparent; border: none; }")

        self.setFixedSize(260, 140)
        self._active_shape_id: str = "shape_line"

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()

    def _build_ui(self) -> None:
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(0)

        self.container = QtWidgets.QFrame(self)
        self.container.setObjectName("ShapePopupContainer")

        shadow = QtWidgets.QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(16)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        container_layout = QtWidgets.QVBoxLayout(self.container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(6)

        lbl_header = QtWidgets.QLabel("FORMAS GEOMÉTRICAS", self.container)
        lbl_header.setObjectName("ShapePopupHeader")
        lbl_header.setStyleSheet("font-size: 9px; font-weight: bold; color: #a1a1aa;")
        container_layout.addWidget(lbl_header)

        self.grid = QtWidgets.QGridLayout()
        self.grid.setSpacing(6)
        self.grid.setContentsMargins(0, 0, 0, 0)

        self.buttons: Dict[str, QtWidgets.QToolButton] = {}
        row, col = 0, 0
        for item in SHAPE_ITEMS:
            sid = item["id"]
            slabel = item["label"]
            sicon = item["icon"]
            stip = item["tooltip"]

            btn = QtWidgets.QToolButton(self.container)
            btn.setFixedSize(74, 46)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            btn.setIconSize(QtCore.QSize(18, 18))
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setObjectName("ShapeGridButton")
            btn.setToolTip(stip)
            btn.setText(slabel)
            btn.setIcon(get_icon(sicon, color="text_main"))

            btn.clicked.connect(lambda _, i=sid, l=slabel: self._on_shape_clicked(i, l))

            self.grid.addWidget(btn, row, col)
            self.buttons[sid] = btn

            col += 1
            if col >= 3:
                col = 0
                row += 1

        container_layout.addLayout(self.grid)
        outer_layout.addWidget(self.container)

    def set_active_shape(self, shape_id: str) -> None:
        self._active_shape_id = shape_id
        self._update_button_states()

    def _update_button_states(self) -> None:
        theme = ThemeManager.instance()
        accent = theme.get_color("accent") or "#6366f1"
        border = theme.get_color("border") or "#2e2e38"
        bg_hover = theme.get_color("accent_muted") or "rgba(99, 102, 241, 0.15)"
        text_main = theme.get_color("text_main") or "#f3f4f6"

        for sid, btn in self.buttons.items():
            is_active = (sid == self._active_shape_id)
            if is_active:
                btn.setIcon(get_icon(sid, color="#ffffff"))
                btn.setStyleSheet(f"""
                    QToolButton#ShapeGridButton {{
                        background-color: {accent};
                        border: 1px solid {accent};
                        border-radius: 6px;
                        color: #ffffff;
                        font-size: 9px;
                        font-weight: bold;
                        padding: 2px;
                    }}
                """)
            else:
                btn.setIcon(get_icon(sid, color="text_main"))
                btn.setStyleSheet(f"""
                    QToolButton#ShapeGridButton {{
                        background-color: rgba(255, 255, 255, 0.04);
                        border: 1px solid {border};
                        border-radius: 6px;
                        color: {text_main};
                        font-size: 9px;
                        font-weight: 500;
                        padding: 2px;
                    }}
                    QToolButton#ShapeGridButton:hover {{
                        background-color: {bg_hover};
                        border-color: {accent};
                        color: #ffffff;
                    }}
                """)

    def _on_shape_clicked(self, shape_id: str, label: str) -> None:
        self._active_shape_id = shape_id
        self._update_button_states()
        self.shape_selected.emit(shape_id, label)
        self.close()

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_surface = theme.get_color("bg_surface") or "#18181b"
        border = theme.get_color("border") or "#2e2e38"

        self.container.setStyleSheet(f"""
            QFrame#ShapePopupContainer {{
                background-color: {bg_surface};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """)
        self._update_button_states()


class ShapeDropdown(QtWidgets.QToolButton):
    """
    Botão Dropdown Personalizado de Formas Vetoriais (compacto).
    Abre o ShapeSelectorPopup em grid e sincroniza a forma ativa.
    """

    shape_changed = QtCore.Signal(str, str)  # (shape_id, shape_label)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("ShapeDropdown")
        self.setFixedHeight(24)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.setIconSize(QtCore.QSize(14, 14))

        self._popup: Optional[ShapeSelectorPopup] = None
        self._active_shape_id: str = "shape_line"
        self._active_label: str = "Linha Reta"

        self.set_shape("shape_line", "Linha Reta")
        self.clicked.connect(self._open_popup)

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()

    def set_shape(self, shape_id: str, label: Optional[str] = None) -> None:
        self._active_shape_id = shape_id
        if label is None:
            for item in SHAPE_ITEMS:
                if item["id"] == shape_id:
                    label = item["label"]
                    break
        self._active_label = label or shape_id
        self.setText(f"{self._active_label}  ▾")
        self.setIcon(get_icon(shape_id, color="text_main"))

        if self._popup:
            self._popup.set_active_shape(shape_id)

    def shape_id(self) -> str:
        return self._active_shape_id

    def shape_label(self) -> str:
        return self._active_label

    def _open_popup(self) -> None:
        if self._popup is None:
            self._popup = ShapeSelectorPopup(self.window())
            self._popup.shape_selected.connect(self._on_popup_selected)

        self._popup.set_active_shape(self._active_shape_id)
        pos = self.mapToGlobal(QtCore.QPoint(-6, self.height() + 4))
        self._popup.move(pos)
        self._popup.show()

    def _on_popup_selected(self, shape_id: str, label: str) -> None:
        self.set_shape(shape_id, label)
        self.shape_changed.emit(shape_id, label)

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel") or "#1e1e24"
        border = theme.get_color("border") or "#2e2e38"
        text_main = theme.get_color("text_main") or "#f3f4f6"
        accent = theme.get_color("accent") or "#6366f1"

        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
                color: {text_main};
                text-align: left;
            }}
            QToolButton:hover {{
                border-color: {accent};
            }}
        """)
        self.setIcon(get_icon(self._active_shape_id, color="text_main"))
