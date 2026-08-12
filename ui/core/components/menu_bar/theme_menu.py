from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon
from ui.core.theme.manager import ThemeManager

class ThemeMenu(QtWidgets.QMenu):
    themeSettingsRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Tema", parent)
        self.setup_actions()
        ThemeManager.instance().themeChanged.connect(self._on_theme_changed)

    def setup_actions(self):
        self.action_theme = QtGui.QAction("Aparência...", self)
        self.action_theme.setShortcut("Ctrl+T")
        self.action_theme.setIcon(get_icon("theme"))
        self.action_theme.triggered.connect(self.themeSettingsRequested.emit)
        self.addAction(self.action_theme)

    def _on_theme_changed(self, theme_name: str):
        self.action_theme.setIcon(get_icon("theme"))
