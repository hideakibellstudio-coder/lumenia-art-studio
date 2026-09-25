"""
ui.core.widgets.shape_dropdown — Dropdown Personalizado em Grid para Formas Vetoriais
====================================================================================
Apresenta a seleção de formas vetoriais (Linha, Retângulo, Elipse, Polígono, Estrela)
em um grid popover elegante com ícones SVG e temas dinâmicos, sem poluir a barra lateral.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.infrastructure.icons import get_icon
from ui.infrastructure.theme.manager import ThemeManager
from ui.infrastructure.i18n import tr, I18nManager

SHAPE_ITEMS = [
    {"id": "shape_line", "i18n": "shapes.line", "label": "Linha Reta", "icon": "shape_line", "tooltip": "shapes.line_tooltip", "default_tip": "Linha Reta (Shift: Trava Ângulo)"},
    {"id": "shape_rect", "i18n": "shapes.rectangle", "label": "Retângulo", "icon": "shape_rect", "tooltip": "shapes.rect_tooltip", "default_tip": "Retângulo / Quadrado (Shift: 1:1)"},
    {"id": "shape_ellipse", "i18n": "shapes.ellipse", "label": "Elipse", "icon": "shape_ellipse", "tooltip": "shapes.ellipse_tooltip", "default_tip": "Elipse / Círculo (Shift: 1:1)"},
    {"id": "shape_polygon", "i18n": "shapes.polygon", "label": "Polígono", "icon": "shape_polygon", "tooltip": "shapes.polygon_tooltip", "default_tip": "Polígono Regular (3 a 16 lados)"},
    {"id": "shape_star", "i18n": "shapes.star", "label": "Estrela", "icon": "shape_star", "tooltip": "shapes.star_tooltip", "default_tip": "Estrela Paramétrica (3 a 16 pontas)"},
]


def get_shape_label(shape_id: str) -> str:
    for item in SHAPE_ITEMS:
        if item["id"] == shape_id:
            return tr(item["i18n"], item["label"])
    return shape_id


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
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self._apply_style()

    def _build_ui(self) -> None:
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(0)

        self.container = QtWidgets.QFrame(self)
        self.container.setObjectName("ShapePopupContainer")

        shadow = QtWidgets.QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(16)
        shadow.setColor(ThemeManager.instance().shadow_color(160))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        container_layout = QtWidgets.QVBoxLayout(self.container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(6)

        self.lbl_header = QtWidgets.QLabel(tr("shapes.header", "FORMAS GEOMÉTRICAS"), self.container)
        self.lbl_header.setObjectName("ShapePopupHeader")
        self.lbl_header.setProperty("muted", "true")
        container_layout.addWidget(self.lbl_header)

        self.grid = QtWidgets.QGridLayout()
        self.grid.setSpacing(6)
        self.grid.setContentsMargins(0, 0, 0, 0)

        self.buttons: Dict[str, QtWidgets.QToolButton] = {}
        row, col = 0, 0
        for item in SHAPE_ITEMS:
            sid = item["id"]
            slabel = tr(item["i18n"], item["label"])
            sicon = item["icon"]
            stip = tr(item["tooltip"], item["default_tip"])

            btn = QtWidgets.QToolButton(self.container)
            btn.setFixedSize(74, 46)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            btn.setIconSize(QtCore.QSize(18, 18))
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setObjectName("ShapeGridButton")
            btn.setToolTip(stip)
            btn.setText(slabel)
            btn.setIcon(get_icon(sicon, color="text_main"))

            btn.clicked.connect(lambda _, i=sid: self._on_shape_clicked(i, get_shape_label(i)))

            self.grid.addWidget(btn, row, col)
            self.buttons[sid] = btn

            col += 1
            if col >= 3:
                col = 0
                row += 1

        container_layout.addLayout(self.grid)
        outer_layout.addWidget(self.container)

    def retranslate_ui(self):
        if hasattr(self, "lbl_header"):
            self.lbl_header.setText(tr("shapes.header", "FORMAS GEOMÉTRICAS"))
        for item in SHAPE_ITEMS:
            sid = item["id"]
            if sid in self.buttons:
                btn = self.buttons[sid]
                btn.setText(tr(item["i18n"], item["label"]))
                btn.setToolTip(tr(item["tooltip"], item["default_tip"]))

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
                btn.setIcon(get_icon(sid, color=text_main))
                btn.setStyleSheet(f"""
                    QToolButton#ShapeGridButton {{
                        background-color: {accent};
                        border: 1px solid {accent};
                        border-radius: 6px;
                        color: {text_main};
                        font-size: 9px;
                        font-weight: bold;
                        padding: 2px;
                    }}
                """)
            else:
                btn.setIcon(get_icon(sid, color=text_main))
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
                        color: {text_main};
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

        self.retranslate_ui()
        self.clicked.connect(self._open_popup)

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self._apply_style()

    def retranslate_ui(self):
        lbl = get_shape_label(self._active_shape_id)
        self.setText(f"{lbl}  ▾")

    def set_shape(self, shape_id: str, label: Optional[str] = None) -> None:
        self._active_shape_id = shape_id
        lbl = label or get_shape_label(shape_id)
        self.setText(f"{lbl}  ▾")
        self.setIcon(get_icon(shape_id, color="text_main"))

        if self._popup:
            self._popup.set_active_shape(shape_id)

    def shape_id(self) -> str:
        return self._active_shape_id

    def shape_label(self) -> str:
        return get_shape_label(self._active_shape_id)

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
