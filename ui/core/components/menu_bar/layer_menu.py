"""
LayerMenu — Menu Camada (Padrão Profissional da Indústria) — ARCcC i18n.
========================================================================
Expõe ações de gerenciamento de camadas, grupos, mesclagem, máscaras de corte e alpha lock.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon
from ui.core.i18n import tr


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
        super().__init__("Camadas", parent)
        self.setup_actions()
        self.retranslate_ui()

    def setup_actions(self):
        # 1. Criação & Duplicação
        self.act_new_layer = QtGui.QAction(get_icon("plus"), "", self)
        self.act_new_layer.setShortcut("Ctrl+Shift+N")
        self.act_new_layer.triggered.connect(self.newLayerRequested.emit)
        self.addAction(self.act_new_layer)

        self.act_new_group = QtGui.QAction(get_icon("folder_open"), "", self)
        self.act_new_group.setShortcut("Ctrl+G")
        self.act_new_group.triggered.connect(self.newGroupRequested.emit)
        self.addAction(self.act_new_group)

        self.act_dup = QtGui.QAction(get_icon("duplicate"), "", self)
        self.act_dup.setShortcut("Ctrl+J")
        self.act_dup.triggered.connect(self.duplicateLayerRequested.emit)
        self.addAction(self.act_dup)

        self.act_del = QtGui.QAction(get_icon("trash"), "", self)
        self.act_del.setShortcut("Shift+Delete")
        self.act_del.triggered.connect(self.deleteLayerRequested.emit)
        self.addAction(self.act_del)

        self.addSeparator()

        # 2. Mesclagem
        self.act_merge = QtGui.QAction(get_icon("merge"), "", self)
        self.act_merge.setShortcut("Ctrl+E")
        self.act_merge.triggered.connect(self.mergeDownRequested.emit)
        self.addAction(self.act_merge)

        self.act_flat_grp = QtGui.QAction(get_icon("layers"), "", self)
        self.act_flat_grp.triggered.connect(self.flattenGroupRequested.emit)
        self.addAction(self.act_flat_grp)

        self.act_flat_img = QtGui.QAction(get_icon("image"), "", self)
        self.act_flat_img.triggered.connect(self.flattenImageRequested.emit)
        self.addAction(self.act_flat_img)

        self.addSeparator()

        # 3. Modificadores
        self.act_clip = QtGui.QAction(get_icon("clip_mask"), "", self)
        self.act_clip.setShortcut("Ctrl+Alt+G")
        self.act_clip.triggered.connect(self.toggleClippingRequested.emit)
        self.addAction(self.act_clip)

        self.act_alock = QtGui.QAction(get_icon("alpha_lock"), "", self)
        self.act_alock.setShortcut("/")
        self.act_alock.triggered.connect(self.toggleAlphaLockRequested.emit)
        self.addAction(self.act_alock)

        self.act_vis = QtGui.QAction(get_icon("eye"), "", self)
        self.act_vis.setShortcut("Ctrl+,")
        self.act_vis.triggered.connect(self.toggleVisibilityRequested.emit)
        self.addAction(self.act_vis)

        self.addSeparator()

        self.act_props = QtGui.QAction(get_icon("sliders"), "", self)
        self.act_props.triggered.connect(self.layerPropertiesRequested.emit)
        self.addAction(self.act_props)

    def retranslate_ui(self):
        self.setTitle(tr("menu.layer.title", "Camadas"))
        self.act_new_layer.setText(tr("menu.layer.new", "Nova Camada..."))
        self.act_new_group.setText(tr("menu.layer.new_group", "Novo Grupo de Camadas"))
        self.act_dup.setText(tr("menu.layer.duplicate", "Duplicar Camada / Grupo"))
        self.act_del.setText(tr("menu.layer.delete", "Excluir Camada Ativa"))
        self.act_merge.setText(tr("menu.layer.merge_down", "Mesclar com a de Baixo"))
        self.act_flat_grp.setText(tr("menu.layer.flatten_group", "Achatar Grupo"))
        self.act_flat_img.setText(tr("menu.layer.flatten_image", "Achatar Imagem Completa"))
        self.act_clip.setText(tr("menu.layer.toggle_clipping", "Alternar Máscara de Recorte"))
        self.act_alock.setText(tr("menu.layer.toggle_alpha_lock", "Alternar Bloqueio de Alfa"))
        self.act_vis.setText(tr("menu.layer.toggle_visibility", "Alternar Visibilidade"))
        self.act_props.setText(tr("menu.layer.properties", "Propriedades da Camada..."))
