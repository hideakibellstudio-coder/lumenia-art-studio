"""DynamicStackedWidget that updates sizeHint based on active page."""

from typing import Optional
from PySide6 import QtCore, QtWidgets

class DynamicStackedWidget(QtWidgets.QStackedWidget):
    """QStackedWidget que calcula dinamicamente seu sizeHint baseado na página ativa e notifica redimensionamento."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.currentChanged.connect(self._on_current_changed)

    def _on_current_changed(self, index: int):
        self.updateGeometry()
        p = self.parentWidget()
        if p:
            p.updateGeometry()
        win = self.window()
        if win and isinstance(win, QtWidgets.QDialog):
            win.updateGeometry()
            win.adjustSize()
            parent_ws = win.parent()
            if parent_ws and hasattr(parent_ws, "update_toolbar_position"):
                parent_ws.update_toolbar_position()

    def sizeHint(self) -> QtCore.QSize:
        cur = self.currentWidget()
        if cur is not None:
            return cur.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self) -> QtCore.QSize:
        cur = self.currentWidget()
        if cur is not None:
            return cur.minimumSizeHint()
        return super().minimumSizeHint()
