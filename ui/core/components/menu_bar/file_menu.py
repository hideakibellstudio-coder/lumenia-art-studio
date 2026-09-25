"""
FileMenu — Menu de Arquivo (Padrão Profissional da Indústria) — ARCcC i18n.
==========================================================================
Expõe as opções de Criação de Documento, Abertura, Salvamento, Exportação e Fechamento.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.infrastructure.icons import get_icon
from ui.infrastructure.i18n import tr


class FileMenu(QtWidgets.QMenu):
    newDocumentRequested    = QtCore.Signal()
    openDocumentRequested   = QtCore.Signal()
    saveDocumentRequested   = QtCore.Signal()
    saveAsDocumentRequested = QtCore.Signal()
    exportImageRequested    = QtCore.Signal()
    closeDocumentRequested  = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Arquivo", parent)
        self.setup_actions()
        self.retranslate_ui()

    def setup_actions(self):
        # 1. Criação & Abertura
        self.action_new = QtGui.QAction(get_icon("file_plus"), "", self)
        self.action_new.setShortcut("Ctrl+N")
        self.action_new.triggered.connect(self.newDocumentRequested.emit)
        self.addAction(self.action_new)

        self.action_open = QtGui.QAction(get_icon("folder_open"), "", self)
        self.action_open.setShortcut("Ctrl+O")
        self.action_open.triggered.connect(self.openDocumentRequested.emit)
        self.addAction(self.action_open)

        self.addSeparator()

        # 2. Salvamento & Exportação
        self.action_save = QtGui.QAction(get_icon("save"), "", self)
        self.action_save.setShortcut("Ctrl+S")
        self.action_save.triggered.connect(self.saveDocumentRequested.emit)
        self.addAction(self.action_save)

        self.action_save_as = QtGui.QAction(get_icon("save"), "", self)
        self.action_save_as.setShortcut("Ctrl+Shift+S")
        self.action_save_as.triggered.connect(self.saveAsDocumentRequested.emit)
        self.addAction(self.action_save_as)

        self.action_export = QtGui.QAction(get_icon("export"), "", self)
        self.action_export.setShortcut("Ctrl+E")
        self.action_export.triggered.connect(self.exportImageRequested.emit)
        self.addAction(self.action_export)

        self.addSeparator()

        # 3. Fechamento
        self.action_close = QtGui.QAction(get_icon("close"), "", self)
        self.action_close.setShortcut("Ctrl+W")
        self.action_close.triggered.connect(self.closeDocumentRequested.emit)
        self.addAction(self.action_close)

        self.addSeparator()

        self.action_exit = QtGui.QAction("", self)
        self.action_exit.setShortcut("Ctrl+Q")
        self.action_exit.triggered.connect(QtWidgets.QApplication.closeAllWindows)
        self.addAction(self.action_exit)

    def retranslate_ui(self):
        self.setTitle(tr("menu.file.title", "Arquivo"))
        self.action_new.setText(tr("menu.file.new", "Novo Documento..."))
        self.action_open.setText(tr("menu.file.open", "Abrir Imagem..."))
        self.action_save.setText(tr("menu.file.save", "Salvar"))
        self.action_save_as.setText(tr("menu.file.save_as", "Salvar Como..."))
        self.action_export.setText(tr("menu.file.export", "Exportar Imagem..."))
        self.action_close.setText(tr("menu.file.close", "Fechar Documento"))
        self.action_exit.setText(tr("menu.file.exit", "Sair"))
