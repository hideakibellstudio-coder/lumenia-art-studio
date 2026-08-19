"""
EditMenu — Menu Editar (Padrão Profissional da Indústria)
=========================================================
Expõe ações de Desfazer, Refazer, Copiar, Colar, Preenchimento, Limpeza e Transformação.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore


class EditMenu(QtWidgets.QMenu):
    undoRequested          = QtCore.Signal()
    redoRequested          = QtCore.Signal()
    cutRequested           = QtCore.Signal()
    copyRequested          = QtCore.Signal()
    pasteRequested         = QtCore.Signal()
    fillRequested          = QtCore.Signal()
    clearLayerRequested    = QtCore.Signal()
    clearCanvasRequested   = QtCore.Signal()
    freeTransformRequested = QtCore.Signal()
    preferencesRequested   = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Editar", parent)
        self.setup_actions()

    def setup_actions(self):
        # 1. Histórico (Undo / Redo)
        act_undo = QtGui.QAction("↩ Desfazer", self)
        act_undo.setShortcut("Ctrl+Z")
        act_undo.triggered.connect(self.undoRequested.emit)
        self.addAction(act_undo)

        act_redo = QtGui.QAction("↪ Refazer", self)
        act_redo.setShortcut("Ctrl+Y")
        act_redo.triggered.connect(self.redoRequested.emit)
        self.addAction(act_redo)

        self.addSeparator()

        # 2. Área de Transferência
        act_cut = QtGui.QAction("✂ Cortar", self)
        act_cut.setShortcut("Ctrl+X")
        act_cut.triggered.connect(self.cutRequested.emit)
        self.addAction(act_cut)

        act_copy = QtGui.QAction("📋 Copiar", self)
        act_copy.setShortcut("Ctrl+C")
        act_copy.triggered.connect(self.copyRequested.emit)
        self.addAction(act_copy)

        act_paste = QtGui.QAction("📥 Colar", self)
        act_paste.setShortcut("Ctrl+V")
        act_paste.triggered.connect(self.pasteRequested.emit)
        self.addAction(act_paste)

        self.addSeparator()

        # 3. Preenchimento & Limpeza
        act_fill = QtGui.QAction("🎨 Preencher com Cor Ativa...", self)
        act_fill.setShortcut("Shift+F5")
        act_fill.triggered.connect(self.fillRequested.emit)
        self.addAction(act_fill)

        act_clear_layer = QtGui.QAction("🧹 Limpar Camada Ativa", self)
        act_clear_layer.setShortcut("Delete")
        act_clear_layer.triggered.connect(self.clearLayerRequested.emit)
        self.addAction(act_clear_layer)

        act_clear_all = QtGui.QAction("🗑 Limpar Todo o Canvas", self)
        act_clear_all.triggered.connect(self.clearCanvasRequested.emit)
        self.addAction(act_clear_all)

        self.addSeparator()

        # 4. Transformações
        act_transform = QtGui.QAction("🔄 Transformação Livre...", self)
        act_transform.setShortcut("Ctrl+T")
        act_transform.triggered.connect(self.freeTransformRequested.emit)
        self.addAction(act_transform)

        self.addSeparator()

        # 5. Preferências
        act_prefs = QtGui.QAction("⚙ Preferências do Sistema...", self)
        act_prefs.setShortcut("Ctrl+K")
        act_prefs.triggered.connect(self.preferencesRequested.emit)
        self.addAction(act_prefs)
