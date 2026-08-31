"""
SelectMenu — Menu Seleção (Padrão Profissional da Indústria) — ARCcC i18n.
==========================================================================
Expõe ações de seleção global, desseleção, inversão, modificação e varinha mágica.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon
from ui.core.i18n import tr


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
        self.retranslate_ui()

    def setup_actions(self):
        # 1. Seleções Globais
        self.act_all = QtGui.QAction(get_icon("select_rect"), "", self)
        self.act_all.setShortcut("Ctrl+A")
        self.act_all.triggered.connect(self.selectAllRequested.emit)
        self.addAction(self.act_all)

        self.act_desel = QtGui.QAction(get_icon("close"), "", self)
        self.act_desel.setShortcut("Ctrl+D")
        self.act_desel.triggered.connect(self.deselectRequested.emit)
        self.addAction(self.act_desel)

        self.act_inv = QtGui.QAction(get_icon("rotate_cw"), "", self)
        self.act_inv.setShortcut("Ctrl+Shift+I")
        self.act_inv.triggered.connect(self.invertSelectionRequested.emit)
        self.addAction(self.act_inv)

        self.addSeparator()

        # 2. Modificações de Seleção
        self.menu_modify = QtWidgets.QMenu("", self)
        self.menu_modify.setIcon(get_icon("ruler"))

        self.act_expand = QtGui.QAction(get_icon("plus"), "", self)
        self.act_expand.triggered.connect(self.expandSelectionRequested.emit)
        self.menu_modify.addAction(self.act_expand)

        self.act_contract = QtGui.QAction(get_icon("transform"), "", self)
        self.act_contract.triggered.connect(self.contractSelectionRequested.emit)
        self.menu_modify.addAction(self.act_contract)

        self.act_feather = QtGui.QAction(get_icon("blur"), "", self)
        self.act_feather.setShortcut("Shift+F6")
        self.act_feather.triggered.connect(self.featherSelectionRequested.emit)
        self.menu_modify.addAction(self.act_feather)

        self.addMenu(self.menu_modify)

        self.addSeparator()

        self.act_wand = QtGui.QAction(get_icon("wand"), "", self)
        self.act_wand.setShortcut("W")
        self.act_wand.triggered.connect(self.magicWandRequested.emit)
        self.addAction(self.act_wand)

    def retranslate_ui(self):
        self.setTitle(tr("menu.select.title", "Seleção"))
        self.act_all.setText(tr("menu.select.all", "Selecionar Tudo"))
        self.act_desel.setText(tr("menu.select.deselect", "Desmarcar Seleção"))
        self.act_inv.setText(tr("menu.select.invert", "Inverter Seleção"))
        self.menu_modify.setTitle(tr("menu.select.modify_menu", "Modificar Seleção"))
        self.act_expand.setText(tr("menu.select.expand", "Expandir Seleção..."))
        self.act_contract.setText(tr("menu.select.contract", "Contrair Seleção..."))
        self.act_feather.setText(tr("menu.select.feather", "Suavizar Borda (Feather)..."))
        self.act_wand.setText(tr("tools.wand", "Varinha Mágica"))
