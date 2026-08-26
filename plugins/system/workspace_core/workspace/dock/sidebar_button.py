"""SidebarButton component for Workspace Dock System."""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager


class SidebarButton(QtWidgets.QToolButton):
    """Botão de ícone da sidebar com suporte a drag & drop de reordenação."""

    def __init__(
        self,
        panel_id: str,
        title: str,
        icon_path: str | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.panel_id = panel_id
        self.setCheckable(True)
        self.setFixedSize(44, 44)
        self.setToolTip(title)

        if icon_path and QtCore.QFile.exists(icon_path):
            self.setIcon(QtGui.QIcon(icon_path))
            self.setIconSize(QtCore.QSize(22, 22))
        else:
            self.setText(title[0].upper() if title else "?")

        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._drag_start_pos: QtCore.QPoint | None = None

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_normal = theme.get_color("bg_panel")
        bg_hover  = theme.get_color("accent_muted")
        bg_active = theme.get_color("accent")
        text_main = theme.get_color("text_main")
        border    = theme.get_color("border")

        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {bg_normal};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }}
            QToolButton:hover {{
                background-color: {bg_hover};
                border-color: {bg_active};
            }}
            QToolButton:checked {{
                background-color: {bg_active};
                color: #ffffff;
                border: 1px solid {bg_active};
            }}
        """)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if (
            event.buttons() & QtCore.Qt.LeftButton
            and self._drag_start_pos is not None
        ):
            delta = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            if delta >= QtWidgets.QApplication.startDragDistance():
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def _start_drag(self) -> None:
        self._drag_start_pos = None
        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        mime.setData("application/x-lumenia-panel", self.panel_id.encode("utf-8"))
        drag.setMimeData(mime)

        pix = self.grab()
        drag.setPixmap(pix)
        drag.setHotSpot(pix.rect().center())
        drag.exec(QtCore.Qt.MoveAction)
