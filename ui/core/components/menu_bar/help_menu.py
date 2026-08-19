"""
HelpMenu — Menu Ajuda
=====================
Expõe atalhos de teclado, guia rápido, diagnósticos do motor e informações sobre o software.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore


class HelpMenu(QtWidgets.QMenu):
    shortcutsRequested   = QtCore.Signal()
    userGuideRequested   = QtCore.Signal()
    diagnosticsRequested = QtCore.Signal()
    aboutRequested       = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Ajuda", parent)
        self.setup_actions()

    def setup_actions(self):
        act_shortcuts = QtGui.QAction("⌨ Atalhos de Teclado", self)
        act_shortcuts.setShortcut("F1")
        act_shortcuts.triggered.connect(self.shortcutsRequested.emit)
        self.addAction(act_shortcuts)

        act_guide = QtGui.QAction("📖 Guia do Usuário...", self)
        act_guide.triggered.connect(self.userGuideRequested.emit)
        self.addAction(act_guide)

        self.addSeparator()

        act_diag = QtGui.QAction("📊 Diagnósticos do Motor & Telemetria", self)
        act_diag.triggered.connect(self.diagnosticsRequested.emit)
        self.addAction(act_diag)

        self.addSeparator()

        act_about = QtGui.QAction("ℹ Sobre o Lumenia...", self)
        act_about.triggered.connect(self.aboutRequested.emit)
        self.addAction(act_about)
