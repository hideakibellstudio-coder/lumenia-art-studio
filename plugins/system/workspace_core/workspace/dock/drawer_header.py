"""DrawerHeader component for Workspace Dock System."""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


class DrawerHeader(QtWidgets.QWidget):
    """Barra superior da gaveta (Título + Botão Pin 📌)."""

    pin_toggled = QtCore.Signal(bool)

    def __init__(self, title: str = "", side: str = "left", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.side = side
        self.setFixedHeight(34)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        from ui.core.i18n import tr, I18nManager
        self.title_label = QtWidgets.QLabel(title.upper(), self)

        self.btn_pin = QtWidgets.QToolButton(self)
        self.btn_pin.setCheckable(True)
        self.btn_pin.setToolTip(tr("window.pin_dock", "Fixar Doca no Layout (Pin)"))
        self.btn_pin.setFixedSize(24, 24)
        self.btn_pin.setIconSize(QtCore.QSize(14, 14))
        self.btn_pin.setIcon(get_icon("pin"))
        self.btn_pin.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_pin.toggled.connect(self.pin_toggled)

        if self.side == "left":
            self.title_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            layout.addStretch()
            layout.addWidget(self.title_label)
            layout.addWidget(self.btn_pin)
        else:
            self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            layout.addWidget(self.btn_pin)
            layout.addWidget(self.title_label)
            layout.addStretch()

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self._apply_style()

    def retranslate_ui(self):
        from ui.core.i18n import tr
        if hasattr(self, "btn_pin"):
            self.btn_pin.setToolTip(tr("window.pin_dock", "Fixar Doca no Layout (Pin)"))

    def set_title(self, title: str) -> None:
        self.title_label.setText(title.upper())

    def set_pinned(self, pinned: bool) -> None:
        self.btn_pin.blockSignals(True)
        self.btn_pin.setChecked(pinned)
        self.btn_pin.blockSignals(False)

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_header = theme.get_color("bg_panel", "#1e1e24")
        text_main = theme.get_color("text_main", "#f3f4f6")
        border    = theme.get_color("border",    "#2e2e38")

        c = QtGui.QColor(bg_header)
        p = self.palette()
        p.setColor(QtGui.QPalette.Window, c)
        p.setColor(QtGui.QPalette.Base, c)
        self.setPalette(p)

        self.title_label.setStyleSheet(
            f"color: {text_main}; font-weight: bold; font-size: 11px; "
            "background-color: transparent; border: none;"
        )
        self.setStyleSheet(f"""
            DrawerHeader {{
                background-color: {bg_header};
                border-bottom: 1px solid {border};
            }}
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                color: {text_main};
                font-size: 11px;
            }}
            QToolButton:hover {{
                background-color: rgba(150, 150, 150, 0.15);
            }}
            QToolButton:checked {{
                background-color: rgba(99, 102, 241, 0.3);
            }}
        """)
