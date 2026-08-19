"""
SelectMenu — Menu Seleção (Padrão Profissional da Indústria)
============================================================
Expõe ações de seleção global, desseleção, inversão, modificação e varinha mágica.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore


class SelectMenu(QtWidgets.QMenu):
    selectAllRequested        = QtCore.Signal()
    deselectRequested         = QtCore.Signal()
    invertSelectionRequested  = QtCore.Signal()
    expandSelectionRequested  = QtCore.Signal()
    contractSelectionRequested = QtCore.Signal()
    featherSelectionRequested = QtCore.Signal()
    magicWandRequested        = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Seleção", parent)
        self.setup_actions()

    def setup_actions(self):
        # 1. Seleções Globais
        act_all = QtGui.QAction("🔲 Selecionar Tudo", self)
        act_all.setShortcut("Ctrl+A")
        act_all.triggered.connect(self.selectAllRequested.emit)
        self.addAction(act_all)

        act_desel = QtGui.QAction("✖ Desmarcar Seleção", self)
        act_desel.setShortcut("Ctrl+D")
        act_desel.triggered.connect(self.deselectRequested.emit)
        self.addAction(act_desel)

        act_inv = QtGui.QAction("🔄 Inverter Seleção", self)
        act_inv.setShortcut("Ctrl+Shift+I")
        act_inv.triggered.connect(self.invertSelectionRequested.emit)
        self.addAction(act_inv)

        self.addSeparator()

        # 2. Modificações de Seleção
        menu_modify = QtWidgets.QMenu("📐 Modificar Seleção", self)

        act_expand = QtGui.QAction("Expandir Seleção...", self)
        act_expand.triggered.connect(self.expandSelectionRequested.emit)
        menu_modify.addAction(act_expand)

        act_contract = QtGui.QAction("Contrair Seleção...", self)
        act_contract.triggered.connect(self.contractSelectionRequested.emit)
        menu_modify.addAction(act_contract)

        act_feather = QtGui.QAction("Suavizar Borda (Feather)...", self)
        act_feather.setShortcut("Shift+F6")
        act_feather.triggered.connect(self.featherSelectionRequested.emit)
        menu_modify.addAction(act_feather)

        self.addMenu(menu_modify)

        self.addSeparator()

        # 3. Ferramenta Varinha Mágica
        act_wand = QtGui.QAction("🪄 Selecionar por Cor (Varinha Mágica)", self)
        act_wand.setShortcut("W")
        act_wand.triggered.connect(self.magicWandRequested.emit)
        self.addAction(act_wand)
