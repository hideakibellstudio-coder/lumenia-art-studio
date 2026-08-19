"""
LayerMenu — Menu Camada (Padrão Profissional da Indústria)
==========================================================
Expõe ações de gerenciamento de camadas, grupos, mesclagem, máscaras de corte e alpha lock.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore


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
        act_new_layer = QtGui.QAction("➕ Nova Camada...", self)
        act_new_layer.setShortcut("Ctrl+Shift+N")
        act_new_layer.triggered.connect(self.newLayerRequested.emit)
        self.addAction(act_new_layer)

        act_new_group = QtGui.QAction("📁 Novo Grupo de Camadas", self)
        act_new_group.setShortcut("Ctrl+G")
        act_new_group.triggered.connect(self.newGroupRequested.emit)
        self.addAction(act_new_group)

        act_dup = QtGui.QAction("📄 Duplicar Camada", self)
        act_dup.setShortcut("Ctrl+J")
        act_dup.triggered.connect(self.duplicateLayerRequested.emit)
        self.addAction(act_dup)

        act_del = QtGui.QAction("🗑 Excluir Camada", self)
        act_del.setShortcut("Shift+Delete")
        act_del.triggered.connect(self.deleteLayerRequested.emit)
        self.addAction(act_del)

        self.addSeparator()

        # 2. Mesclagem
        act_merge = QtGui.QAction("⬇ Mesclar com a de Baixo", self)
        act_merge.setShortcut("Ctrl+E")
        act_merge.triggered.connect(self.mergeDownRequested.emit)
        self.addAction(act_merge)

        act_flat_grp = QtGui.QAction("📦 Achatar Grupo", self)
        act_flat_grp.triggered.connect(self.flattenGroupRequested.emit)
        self.addAction(act_flat_grp)

        act_flat_all = QtGui.QAction("🖼 Achatar Imagem Completa", self)
        act_flat_all.triggered.connect(self.flattenImageRequested.emit)
        self.addAction(act_flat_all)

        self.addSeparator()

        # 3. Modos Especiais de Camada
        act_clip = QtGui.QAction("✂ Máscara de Corte (Clipping Mask)", self)
        act_clip.setShortcut("Ctrl+Alt+G")
        act_clip.triggered.connect(self.toggleClippingRequested.emit)
        self.addAction(act_clip)

        act_alpha = QtGui.QAction("🔒 Bloquear Transparência (Alpha Lock)", self)
        act_alpha.setShortcut("Ctrl+/")
        act_alpha.triggered.connect(self.toggleAlphaLockRequested.emit)
        self.addAction(act_alpha)

        act_vis = QtGui.QAction("👁 Alternar Visibilidade da Camada", self)
        act_vis.setShortcut("Ctrl+,")
        act_vis.triggered.connect(self.toggleVisibilityRequested.emit)
        self.addAction(act_vis)

        self.addSeparator()

        # 4. Propriedades
        act_props = QtGui.QAction("⚙ Propriedades da Camada...", self)
        act_props.triggered.connect(self.layerPropertiesRequested.emit)
        self.addAction(act_props)
