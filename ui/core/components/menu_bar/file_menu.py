"""
FileMenu — Menu de Arquivo com Ações do ALADYN ENGINE
=====================================================
Expõe as opções de Documento, Exportação PNG/JPG, Limpeza e Saída.
"""

from PySide6 import QtWidgets, QtGui, QtCore


class FileMenu(QtWidgets.QMenu):
    newDocumentRequested   = QtCore.Signal()
    closeDocumentRequested = QtCore.Signal()
    exportImageRequested   = QtCore.Signal()
    clearCanvasRequested   = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Arquivo", parent)
        self.setup_actions()

    def setup_actions(self):
        # 1. Documentos
        action_new = QtGui.QAction("📄 Novo Documento...", self)
        action_new.setShortcut("Ctrl+N")
        action_new.triggered.connect(self.newDocumentRequested.emit)
        self.addAction(action_new)

        action_close = QtGui.QAction("❌ Fechar Documento", self)
        action_close.setShortcut("Ctrl+W")
        action_close.triggered.connect(self.closeDocumentRequested.emit)
        self.addAction(action_close)

        self.addSeparator()

        # 2. Exportação
        action_export = QtGui.QAction("💾 Exportar Imagem (PNG/JPG)...", self)
        action_export.setShortcut("Ctrl+S")
        action_export.triggered.connect(self.exportImageRequested.emit)
        self.addAction(action_export)

        self.addSeparator()

        # 3. Ferramentas de Edição Rápidas
        action_clear = QtGui.QAction("🧹 Limpar Camada Ativa", self)
        action_clear.setShortcut("Ctrl+Alt+C")
        action_clear.triggered.connect(self.clearCanvasRequested.emit)
        self.addAction(action_clear)

        self.addSeparator()

        # 4. Saída
        action_exit = QtGui.QAction("🚪 Sair", self)
        action_exit.setShortcut("Ctrl+Q")
        action_exit.triggered.connect(QtWidgets.QApplication.instance().quit)
        self.addAction(action_exit)
