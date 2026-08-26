"""SidebarWidget component for Workspace Dock System."""

from typing import Dict, List
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.logger import get_logger
from .sidebar_button import SidebarButton

logger = get_logger("Workspace.DockSystem.Sidebar")


class SidebarWidget(QtWidgets.QWidget):
    """Sidebar de ícones vertical animável (0px ↔ 54px) na borda externa."""

    button_clicked = QtCore.Signal(str)  # panel_id

    def __init__(self, side: str = "left", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.side = side

        self.setMinimumWidth(0)
        self.setMaximumWidth(54)
        self.setAcceptDrops(True)

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(5, 8, 5, 8)
        self._layout.setSpacing(6)
        self._layout.setAlignment(QtCore.Qt.AlignTop)

        self._buttons: Dict[str, SidebarButton] = {}

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        border   = theme.get_color("border",   "#2e2e38")

        border_side = "border-right" if self.side == "left" else "border-left"
        self.setStyleSheet(f"""
            SidebarWidget {{
                background-color: {bg_panel};
                {border_side}: 1px solid {border};
                border-top: 1px solid {border};
                border-bottom: 1px solid {border};
            }}
        """)

    def add_panel_button(self, panel_id: str, title: str, icon_path: str | None = None) -> SidebarButton:
        if panel_id in self._buttons:
            return self._buttons[panel_id]
        btn = SidebarButton(panel_id, title, icon_path, self)
        btn.clicked.connect(lambda: self.button_clicked.emit(panel_id))
        self._buttons[panel_id] = btn
        self._layout.addWidget(btn)
        return btn

    def remove_panel_button(self, panel_id: str) -> None:
        btn = self._buttons.pop(panel_id, None)
        if btn:
            try:
                self._layout.removeWidget(btn)
                btn.deleteLater()
            except RuntimeError:
                pass

    def set_button_active(self, panel_id: str, active: bool) -> None:
        btn = self._buttons.get(panel_id)
        if btn:
            try:
                btn.blockSignals(True)
                btn.setChecked(active)
                btn.blockSignals(False)
            except RuntimeError:
                pass

    def get_panel_order(self) -> List[str]:
        """Retorna a lista de panel_ids na ordem visual dos botões."""
        order = []
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), "panel_id"):
                order.append(item.widget().panel_id)
        return order

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasFormat("application/x-lumenia-panel"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if event.mimeData().hasFormat("application/x-lumenia-panel"):
            event.acceptProposedAction()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if not event.mimeData().hasFormat("application/x-lumenia-panel"):
            event.ignore()
            return

        pid = event.mimeData().data("application/x-lumenia-panel").data().decode("utf-8")
        btn = self._buttons.get(pid)
        if not btn:
            event.ignore()
            return

        drop_y = event.position().toPoint().y()
        target_idx = self._layout.count()
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if not item or not item.widget():
                continue
            w = item.widget()
            center_y = w.y() + w.height() // 2
            if drop_y < center_y:
                target_idx = i
                break

        self._layout.removeWidget(btn)
        self._layout.insertWidget(target_idx, btn)
        event.acceptProposedAction()

        logger.info(f"Sidebar '{self.side}': reordenou '{pid}' para índice {target_idx}")
