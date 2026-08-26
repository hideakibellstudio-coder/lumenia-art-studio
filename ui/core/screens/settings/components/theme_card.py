"""Components for Theme Settings Dialog (ThemeCard, Swatches)."""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


class ColorDot(QtWidgets.QFrame):
    """Círculo colorido representativo de um canal de cor."""

    def __init__(self, color_hex: str, size: int = 14, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setStyleSheet(f"""
            background-color: {color_hex};
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: {size // 2}px;
        """)


class ThemeMiniSwatches(QtWidgets.QWidget):
    """Grupo de 4 cores principais do tema."""

    def __init__(self, colors: dict, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        bg = colors.get("bg_main") or colors.get("BG_DARKEST") or "#121212"
        panel = colors.get("bg_panel") or colors.get("BG_DARKER") or "#1e1e1e"
        accent = colors.get("accent") or colors.get("ACCENT") or "#ff5252"
        text = colors.get("text_main") or colors.get("FG_PRIMARY") or "#ffffff"

        layout.addWidget(ColorDot(bg, 14))
        layout.addWidget(ColorDot(panel, 14))
        layout.addWidget(ColorDot(accent, 14))
        layout.addWidget(ColorDot(text, 14))


class ThemeCard(QtWidgets.QFrame):
    """Cartão individual representando um tema na lista esquerda."""

    selected = QtCore.Signal(dict)

    def __init__(self, theme_data: dict, is_selected: bool = False, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.theme_data = theme_data
        self.is_selected = is_selected
        self.is_active = is_active
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._build_ui()
        self.update_style()

    def _build_ui(self):
        self.setFixedHeight(68)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Ícone vetorial de tipo (Sol / Lua)
        meta = self.theme_data.get("metadata", {})
        t_type = meta.get("type", "dark")
        self.icon_btn = QtWidgets.QToolButton()
        self.icon_btn.setFixedSize(32, 32)
        self.icon_btn.setIconSize(QtCore.QSize(18, 18))
        self.icon_btn.setIcon(get_icon("moon" if t_type == "dark" else "sun"))
        self.icon_btn.setStyleSheet("border: none; background-color: rgba(255,255,255,0.06); border-radius: 6px;")
        layout.addWidget(self.icon_btn)

        # Informações do Tema
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setAlignment(QtCore.Qt.AlignVCenter)

        name = meta.get("name") or self.theme_data.get("file", "Tema")
        author = meta.get("author", "Lumenia")
        self.name_label = QtWidgets.QLabel(name)
        self.name_label.setStyleSheet("font-size: 12px; font-weight: bold;")

        self.author_label = QtWidgets.QLabel(f"por {author}")
        self.author_label.setStyleSheet("font-size: 10px; color: #888888;")

        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.author_label)
        layout.addLayout(text_layout)
        layout.addStretch()

        # Swatches e Badge
        right_box = QtWidgets.QVBoxLayout()
        right_box.setSpacing(4)
        right_box.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.swatches = ThemeMiniSwatches(self.theme_data.get("colors", {}))
        right_box.addWidget(self.swatches)

        self.badge_label = QtWidgets.QLabel("ATIVO" if self.is_active else "")
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 1px 5px; border-radius: 4px;" if self.is_active else "color: transparent;"
        )
        right_box.addWidget(self.badge_label)
        layout.addLayout(right_box)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self.selected.emit(self.theme_data)

    def set_active_state(self, is_active: bool):
        self.is_active = is_active
        self.badge_label.setText("ATIVO" if is_active else "")
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 1px 5px; border-radius: 4px;" if is_active else "color: transparent;"
        )
        self.update_style()

    def update_style(self):
        tm = ThemeManager.instance()
        border_color = tm.get_color("accent") if self.is_selected else tm.get_color("border")
        bg_color = tm.get_color("bg_card_hover") if self.is_selected else tm.get_color("bg_card")
        self.setStyleSheet(f"""
            ThemeCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            ThemeCard:hover {{
                border-color: {tm.get_color('accent')};
            }}
        """)
