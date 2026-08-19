"""
FileMenu — Menu de Arquivo (Padrão Profissional da Indústria)
============================================================
Expõe as opções de Criação de Documento, Abertura, Salvamento, Exportação e Fechamento.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore


class FileMenu(QtWidgets.QMenu):
    newDocumentRequested    = QtCore.Signal()
    openDocumentRequested   = QtCore.Signal()
    saveDocumentRequested   = QtCore.Signal()
    saveAsDocumentRequested = QtCore.Signal()
    exportImageRequested    = QtCore.Signal()
    closeDocumentRequested  = QtCore.Signal()
    clearCanvasRequested    = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Arquivo", parent)
        self.setup_actions()

    def setup_actions(self):
        # 1. Criação & Abertura
        action_new = QtGui.QAction("📄 Novo Documento...", self)
        action_new.setShortcut("Ctrl+N")
        action_new.triggered.connect(self.newDocumentRequested.emit)
        self.addAction(action_new)

        action_open = QtGui.QAction("📂 Abrir Imagem...", self)
        action_open.setShortcut("Ctrl+O")
        action_open.triggered.connect(self.openDocumentRequested.emit)
        self.addAction(action_open)

        self.addSeparator()

        # 2. Salvamento & Exportação
        action_save = QtGui.QAction("💾 Salvar", self)
        action_save.setShortcut("Ctrl+S")
        action_save.triggered.connect(self.saveDocumentRequested.emit)
        self.addAction(action_save)

        action_save_as = QtGui.QAction("💾 Salvar Como...", self)
        action_save_as.setShortcut("Ctrl+Shift+S")
        action_save_as.triggered.connect(self.saveAsDocumentRequested.emit)
        self.addAction(action_save_as)

        action_export = QtGui.QAction("📤 Exportar Imagem (PNG/JPG/BMP)...", self)
        action_export.setShortcut("Ctrl+E")
        action_export.triggered.connect(self.exportImageRequested.emit)
        self.addAction(action_export)

        self.addSeparator()

        # 3. Fechamento
        action_close = QtGui.QAction("❌ Fechar Documento", self)
        action_close.setShortcut("Ctrl+W")
        action_close.triggered.connect(self.closeDocumentRequested.emit)
        self.addAction(action_close)

        self.addSeparator()

        # 4. Saída
        action_exit = QtGui.QAction("🚪 Sair do Lumenia", self)
        action_exit.setShortcut("Ctrl+Q")
        action_exit.triggered.connect(QtWidgets.QApplication.instance().quit)
        self.addAction(action_exit)
