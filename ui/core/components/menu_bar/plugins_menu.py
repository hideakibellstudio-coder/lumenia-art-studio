from PySide6 import QtWidgets, QtCore

class PluginsMenu(QtWidgets.QMenu):
    managePluginsRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Plugins", parent)
        self.setup_actions()

    def setup_actions(self):
        action_manage = self.addAction("Gerenciar Plugins...")
        action_manage.triggered.connect(self.managePluginsRequested.emit)
