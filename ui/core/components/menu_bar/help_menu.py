"""
HelpMenu — Menu Ajuda — ARCcC i18n.
====================================
Expõe atalhos de teclado, guia rápido, diagnósticos do motor e informações sobre o software.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.infrastructure.icons import get_icon
from ui.infrastructure.i18n import tr


class HelpMenu(QtWidgets.QMenu):
    shortcutsRequested   = QtCore.Signal()
    userGuideRequested   = QtCore.Signal()
    testReportRequested  = QtCore.Signal()
    diagnosticsRequested = QtCore.Signal()
    feedbackRequested    = QtCore.Signal()
    aboutRequested       = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Ajuda", parent)
        self.setup_actions()
        self.retranslate_ui()

    def setup_actions(self):
        self.act_shortcuts = QtGui.QAction(get_icon("keyboard"), "", self)
        self.act_shortcuts.setShortcut("F1")
        self.act_shortcuts.triggered.connect(self.shortcutsRequested.emit)
        self.addAction(self.act_shortcuts)

        self.act_guide = QtGui.QAction(get_icon("help"), "", self)
        self.act_guide.triggered.connect(self.userGuideRequested.emit)
        self.addAction(self.act_guide)

        self.act_test_report = QtGui.QAction(get_icon("check"), "", self)
        self.act_test_report.triggered.connect(self.testReportRequested.emit)
        self.addAction(self.act_test_report)

        self.addSeparator()

        self.act_diag = QtGui.QAction(get_icon("chart"), "", self)
        self.act_diag.triggered.connect(self.diagnosticsRequested.emit)
        self.addAction(self.act_diag)

        self.act_feedback = QtGui.QAction(get_icon("help"), "", self)
        self.act_feedback.triggered.connect(self.feedbackRequested.emit)
        self.addAction(self.act_feedback)

        self.addSeparator()

        self.act_about = QtGui.QAction(get_icon("info"), "", self)
        self.act_about.triggered.connect(self.aboutRequested.emit)
        self.addAction(self.act_about)

    def retranslate_ui(self):
        self.setTitle(tr("menu.help.title", "Ajuda"))
        self.act_shortcuts.setText(tr("menu.help.shortcuts", "Atalhos de Teclado"))
        self.act_guide.setText(tr("menu.help.guide", "Guia do Usuário..."))
        self.act_test_report.setText(tr("menu.help.test_report", "Relatório de Testes da Suíte..."))
        self.act_diag.setText(tr("menu.help.diagnostics", "Diagnósticos do Motor & Telemetria"))
        self.act_feedback.setText(tr("menu.help.feedback", "Enviar Feedback / Relatório Alpha..."))
        self.act_about.setText(tr("menu.help.about", "Sobre o Lumenia..."))
