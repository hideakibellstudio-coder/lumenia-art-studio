"""BaseFramelessDialog — Janela e Diálogo Base Padronizado com Design System Lumenia V2."""

from __future__ import annotations
from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


class DialogTitleBar(QtWidgets.QWidget):
    """Barra de título customizada, arrastável e com botão fechar padronizado."""

    def __init__(self, title: str, icon_name: Optional[str] = None, parent_dialog: QtWidgets.QDialog | None = None):
        super().__init__(parent_dialog)
        self._dialog = parent_dialog
        self._drag_pos: Optional[QtCore.QPoint] = None
        self.setObjectName("DialogTitleBar")
        self.setFixedHeight(38)

        self._build_ui(title, icon_name)
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self, title: str, icon_name: Optional[str]):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        # Ícone
        self.lbl_icon = QtWidgets.QLabel()
        self.lbl_icon.setObjectName("DialogTitleIcon")
        self.lbl_icon.setFixedSize(18, 18)
        if icon_name:
            self.lbl_icon.setPixmap(get_icon(icon_name).pixmap(QtCore.QSize(16, 16)))
            self.lbl_icon.setVisible(True)
        else:
            self.lbl_icon.setVisible(False)
        layout.addWidget(self.lbl_icon)

        # Título
        self.lbl_title = QtWidgets.QLabel(title)
        self.lbl_title.setObjectName("DialogTitleLabel")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 12px; letter-spacing: 0.5px;")
        layout.addWidget(self.lbl_title)

        layout.addStretch()

        # Botão Fechar
        self.btn_close = QtWidgets.QToolButton()
        self.btn_close.setObjectName("DialogCloseBtn")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setIconSize(QtCore.QSize(14, 14))
        self.btn_close.setIcon(get_icon("close"))
        self.btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_close.setToolTip("Fechar (Esc)")
        if self._dialog:
            self.btn_close.clicked.connect(self._dialog.reject)
        layout.addWidget(self.btn_close)

    def set_title(self, title: str) -> None:
        self.lbl_title.setText(title)

    def set_icon(self, icon_name: str) -> None:
        self.lbl_icon.setPixmap(get_icon(icon_name).pixmap(QtCore.QSize(16, 16)))
        self.lbl_icon.setVisible(True)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and self._dialog:
            self._drag_pos = event.globalPosition().toPoint() - self._dialog.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_pos and self._dialog and (event.buttons() & QtCore.Qt.LeftButton):
            self._dialog.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag_pos = None

    def _apply_theme(self, *args) -> None:
        theme = ThemeManager.instance()
        text_main = theme.get_color("text_main")
        bg_bar = theme.get_color("bg_panel")
        danger = theme.get_color("danger", "#f43f5e")

        self.setStyleSheet(f"""
            QWidget#DialogTitleBar {{
                background-color: {bg_bar};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            QLabel#DialogTitleLabel {{
                color: {text_main};
            }}
            QToolButton#DialogCloseBtn {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 3px;
            }}
            QToolButton#DialogCloseBtn:hover {{
                background-color: {danger};
            }}
        """)
        self.btn_close.setIcon(get_icon("close", text_main))


class BaseFramelessDialog(QtWidgets.QDialog):
    """Diálogo base padronizado sem bordas de SO, com cabeçalho arrastável, sombra e cantos arredondados."""

    def __init__(
        self,
        title: str = "Diálogo",
        icon_name: Optional[str] = None,
        parent: Optional[QtWidgets.QWidget] = None,
        modal: bool = True
    ):
        flags = QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint
        super().__init__(parent, flags)
        self.setModal(modal)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self._build_base_ui(title, icon_name)
        ThemeManager.instance().themeChanged.connect(self._apply_base_theme)
        self._apply_base_theme()

    def _build_base_ui(self, title: str, icon_name: Optional[str]):
        # Layout raiz da janela que contém o padding para a sombra projetada
        self._outer_layout = QtWidgets.QVBoxLayout(self)
        self._outer_layout.setContentsMargins(10, 10, 10, 10)
        self._outer_layout.setSpacing(0)

        # Container interno estilizado
        self.root_container = QtWidgets.QWidget(self)
        self.root_container.setObjectName("DialogRootContainer")

        # Efeito de Sombra Flutuante (Drop Shadow)
        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QtGui.QColor(0, 0, 0, 140))
        self.shadow.setOffset(0, 4)
        self.root_container.setGraphicsEffect(self.shadow)

        self._container_layout = QtWidgets.QVBoxLayout(self.root_container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)

        # 1. Barra de Título
        self.title_bar = DialogTitleBar(title, icon_name, parent_dialog=self)
        self._container_layout.addWidget(self.title_bar)

        # 2. Divisor Horizontal
        self.header_sep = QtWidgets.QFrame()
        self.header_sep.setObjectName("DialogHeaderSep")
        self.header_sep.setFrameShape(QtWidgets.QFrame.HLine)
        self.header_sep.setFixedHeight(1)
        self._container_layout.addWidget(self.header_sep)

        # 3. Widget e Layout de Conteúdo (onde as subclasses colocam seus widgets)
        self.content_widget = QtWidgets.QWidget()
        self.content_widget.setObjectName("DialogContentWidget")
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(12)

        self._container_layout.addWidget(self.content_widget, 1)
        self._outer_layout.addWidget(self.root_container)

    def set_dialog_title(self, title: str) -> None:
        self.title_bar.set_title(title)

    def set_dialog_icon(self, icon_name: str) -> None:
        self.title_bar.set_icon(icon_name)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def _apply_base_theme(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_card = theme.get_color("bg_main")
        border = theme.get_color("border")
        text_main = theme.get_color("text_main")

        self.root_container.setStyleSheet(f"""
            QWidget#DialogRootContainer {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QFrame#DialogHeaderSep {{
                background-color: {border};
                border: none;
            }}
            QWidget#DialogContentWidget {{
                background-color: transparent;
                color: {text_main};
            }}
        """)
