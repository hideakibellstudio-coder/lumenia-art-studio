"""
LayerMenu — Menu Camada (Padrão Profissional da Indústria)
==========================================================
Expõe ações de gerenciamento de camadas, grupos, mesclagem, máscaras de corte e alpha lock.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon


class LayerMenu(QtWidgets.QMenu):
    newLayerRequested         = QtCore.Signal()
    newGroupRequested         = QtCore.Signal()
    duplicateLayerRequested   = QtCore.Signal()
    deleteLayerRequested      = QtCore.Signal()
    mergeDownRequested        = QtCore.Signal()
    flattenGroupRequested     = QtCore.Signal()
    flattenImageRequested     = QtCore.Signal()
    toggleClippingRequested   = QtCore.Signal()
    toggleAlphaLockRequested  = QtCore.Signal()
    toggleVisibilityRequested = QtCore.Signal()
    layerPropertiesRequested  = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Camada", parent)
        self.setup_actions()

    def setup_actions(self):
        # 1. Criação & Duplicação
        act_new_layer = QtGui.QAction(get_icon("plus"), "Nova Camada...", self)
        act_new_layer.setShortcut("Ctrl+Shift+N")
        act_new_layer.triggered.connect(self.newLayerRequested.emit)
        self.addAction(act_new_layer)

        act_new_group = QtGui.QAction(get_icon("folder_open"), "Novo Grupo de Camadas", self)
        act_new_group.setShortcut("Ctrl+G")
        act_new_group.triggered.connect(self.newGroupRequested.emit)
        self.addAction(act_new_group)

        act_dup = QtGui.QAction(get_icon("duplicate"), "Duplicar Camada", self)
        act_dup.setShortcut("Ctrl+J")
        act_dup.triggered.connect(self.duplicateLayerRequested.emit)
        self.addAction(act_dup)

        act_del = QtGui.QAction(get_icon("trash"), "Excluir Camada", self)
        act_del.setShortcut("Shift+Delete")
        act_del.triggered.connect(self.deleteLayerRequested.emit)
        self.addAction(act_del)

        self.addSeparator()

        # 2. Mesclagem
        act_merge = QtGui.QAction(get_icon("merge"), "Mesclar com a de Baixo", self)
        act_merge.setShortcut("Ctrl+E")
        act_merge.triggered.connect(self.mergeDownRequested.emit)
        self.addAction(act_merge)

        act_flat_grp = QtGui.QAction(get_icon("layers"), "Achatar Grupo", self)
        act_flat_grp.triggered.connect(self.flattenGroupRequested.emit)
        self.addAction(act_flat_grp)

        act_flat_img = QtGui.QAction(get_icon("image"), "Achatar Imagem Completa", self)
        act_flat_img.triggered.connect(self.flattenImageRequested.emit)
        self.addAction(act_flat_img)

        self.addSeparator()

        # 3. Modificadores
        act_clip = QtGui.QAction(get_icon("clip_mask"), "Criar / Liberar Máscara de Corte", self)
        act_clip.setShortcut("Ctrl+Alt+G")
        act_clip.triggered.connect(self.toggleClippingRequested.emit)
        self.addAction(act_clip)

        act_alock = QtGui.QAction(get_icon("alpha_lock"), "Bloquear / Liberar Transparência (Alpha Lock)", self)
        act_alock.setShortcut("/")
        act_alock.triggered.connect(self.toggleAlphaLockRequested.emit)
        self.addAction(act_alock)

        act_vis = QtGui.QAction(get_icon("eye"), "Alternar Visibilidade da Camada", self)
        act_vis.setShortcut("Ctrl+,")
        act_vis.triggered.connect(self.toggleVisibilityRequested.emit)
        self.addAction(act_vis)

        self.addSeparator()

        act_props = QtGui.QAction(get_icon("sliders"), "Propriedades & Opacidade da Camada...", self)
        act_props.triggered.connect(self.layerPropertiesRequested.emit)
        self.addAction(act_props)
