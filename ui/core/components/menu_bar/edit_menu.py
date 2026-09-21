"""
EditMenu — Menu Editar (Padrão Profissional da Indústria) — ARCcC i18n.
========================================================================
Expõe ações de Desfazer, Refazer, Copiar, Colar, Preenchimento, Limpeza e Transformação.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon
from ui.core.i18n import tr


class EditMenu(QtWidgets.QMenu):
    undoRequested          = QtCore.Signal()
    redoRequested          = QtCore.Signal()
    cutRequested           = QtCore.Signal()
    copyRequested          = QtCore.Signal()
    pasteRequested         = QtCore.Signal()
    fillRequested          = QtCore.Signal()
    clearLayerRequested    = QtCore.Signal()
    freeTransformRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Editar", parent)
        self.setup_actions()
        self.retranslate_ui()

    def setup_actions(self):
        # 1. Histórico (Undo / Redo)
        self.act_undo = QtGui.QAction(get_icon("undo"), "", self)
        self.act_undo.setShortcut("Ctrl+Z")
        self.act_undo.triggered.connect(self.undoRequested.emit)
        self.addAction(self.act_undo)

        self.act_redo = QtGui.QAction(get_icon("redo"), "", self)
        self.act_redo.setShortcut("Ctrl+Y")
        self.act_redo.triggered.connect(self.redoRequested.emit)
        self.addAction(self.act_redo)

        self.addSeparator()

        # 2. Área de Transferência
        self.act_cut = QtGui.QAction(get_icon("cut"), "", self)
        self.act_cut.setShortcut("Ctrl+X")
        self.act_cut.triggered.connect(self.cutRequested.emit)
        self.addAction(self.act_cut)

        self.act_copy = QtGui.QAction(get_icon("copy"), "", self)
        self.act_copy.setShortcut("Ctrl+C")
        self.act_copy.triggered.connect(self.copyRequested.emit)
        self.addAction(self.act_copy)

        self.act_paste = QtGui.QAction(get_icon("paste"), "", self)
        self.act_paste.setShortcut("Ctrl+V")
        self.act_paste.triggered.connect(self.pasteRequested.emit)
        self.addAction(self.act_paste)

        self.addSeparator()

        # 3. Preenchimento & Limpeza
        self.act_fill = QtGui.QAction(get_icon("bucket"), "", self)
        self.act_fill.setShortcut("Alt+Backspace")
        self.act_fill.triggered.connect(self.fillRequested.emit)
        self.addAction(self.act_fill)

        self.act_clear_layer = QtGui.QAction(get_icon("clear"), "", self)
        self.act_clear_layer.setShortcut("Del")
        self.act_clear_layer.triggered.connect(self.clearLayerRequested.emit)
        self.addAction(self.act_clear_layer)

        self.addSeparator()

        # 4. Transformação
        self.act_transform = QtGui.QAction(get_icon("transform"), "", self)
        self.act_transform.setShortcut("Ctrl+T")
        self.act_transform.triggered.connect(self.freeTransformRequested.emit)
        self.addAction(self.act_transform)

    def retranslate_ui(self):
        self.setTitle(tr("menu.edit.title", "Editar"))
        self.act_undo.setText(tr("menu.edit.undo", "Desfazer"))
        self.act_undo.setToolTip(tr("menu.edit.undo_tooltip", "Desfaz a última ação realizada"))
        self.act_redo.setText(tr("menu.edit.redo", "Refazer"))
        self.act_redo.setToolTip(tr("menu.edit.redo_tooltip", "Refaz a última ação desfeita"))
        self.act_cut.setText(tr("menu.edit.cut", "Cortar"))
        self.act_copy.setText(tr("menu.edit.copy", "Copiar"))
        self.act_paste.setText(tr("menu.edit.paste", "Colar"))
        self.act_fill.setText(tr("menu.edit.fill", "Preencher Seleção com Cor Ativa"))
        self.act_clear_layer.setText(tr("menu.edit.clear", "Limpar Conteúdo da Camada"))
        self.act_transform.setText(tr("menu.edit.transform", "Transformação Livre..."))
