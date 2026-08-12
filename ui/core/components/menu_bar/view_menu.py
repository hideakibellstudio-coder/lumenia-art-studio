"""
ViewMenu — Menu Exibir com Controles de Zoom e Câmera do ALADYN ENGINE
========================================================================
Renomeado para 'Exibir', espelhando a barra de menus do ALADYN ENGINE.
"""

from PySide6 import QtWidgets, QtGui, QtCore


class ViewMenu(QtWidgets.QMenu):
    zoomInRequested        = QtCore.Signal()
    zoomOutRequested       = QtCore.Signal()
    resetViewRequested     = QtCore.Signal()
    resetRotationRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Exibir", parent)
        self.setup_actions()

    def setup_actions(self):
        # 1. Controles de Zoom
        action_zoom_in = QtGui.QAction("🔍 Aproximar (Zoom In)", self)
        action_zoom_in.setShortcut("Ctrl+=")
        action_zoom_in.triggered.connect(self.zoomInRequested.emit)
        self.addAction(action_zoom_in)

        action_zoom_out = QtGui.QAction("🔍 Afastar (Zoom Out)", self)
        action_zoom_out.setShortcut("Ctrl+-")
        action_zoom_out.triggered.connect(self.zoomOutRequested.emit)
        self.addAction(action_zoom_out)

        self.addSeparator()

        # 2. Reset de Câmera
        action_reset = QtGui.QAction("📐 Zoom 100% (Tamanho Real)", self)
        action_reset.setShortcut("Ctrl+0")
        action_reset.triggered.connect(self.resetViewRequested.emit)
        self.addAction(action_reset)

        action_reset_rot = QtGui.QAction("🔄 Resetar Visão e Rotação", self)
        action_reset_rot.triggered.connect(self.resetRotationRequested.emit)
        self.addAction(action_reset_rot)
