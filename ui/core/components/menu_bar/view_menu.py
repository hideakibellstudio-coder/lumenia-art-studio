"""
ViewMenu — Menu Exibir (Padrão Profissional da Indústria)
=========================================================
Expõe controles de Zoom, Ajuste à Tela, Reset de Câmera, Prova de Cores e Guias do Canvas.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore


class ViewMenu(QtWidgets.QMenu):
    zoomInRequested        = QtCore.Signal()
    zoomOutRequested       = QtCore.Signal()
    resetViewRequested     = QtCore.Signal()
    fitToScreenRequested   = QtCore.Signal()
    resetRotationRequested = QtCore.Signal()
    renderSettingsRequested = QtCore.Signal()
    toggleGridRequested    = QtCore.Signal()
    toggleRulersRequested  = QtCore.Signal()

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

        # 2. Enquadramento e Câmera
        action_reset = QtGui.QAction("📐 Zoom 100% (Tamanho Real)", self)
        action_reset.setShortcut("Ctrl+0")
        action_reset.triggered.connect(self.resetViewRequested.emit)
        self.addAction(action_reset)

        action_fit = QtGui.QAction("🖥 Ajustar à Tela", self)
        action_fit.setShortcut("Ctrl+Alt+0")
        action_fit.triggered.connect(self.fitToScreenRequested.emit)
        self.addAction(action_fit)

        action_reset_rot = QtGui.QAction("🔄 Resetar Rotação e Ângulo", self)
        action_reset_rot.setShortcut("Ctrl+R")
        action_reset_rot.triggered.connect(self.resetRotationRequested.emit)
        self.addAction(action_reset_rot)

        self.addSeparator()

        # 3. Prova de Cores & Renderização
        action_proof = QtGui.QAction("🎨 Prova de Cores & Renderização...", self)
        action_proof.triggered.connect(self.renderSettingsRequested.emit)
        self.addAction(action_proof)

        self.addSeparator()

        # 4. Guias Visuais
        action_grid = QtGui.QAction("▦ Mostrar Grade do Canvas", self)
        action_grid.setShortcut("Ctrl+'")
        action_grid.setCheckable(True)
        action_grid.triggered.connect(self.toggleGridRequested.emit)
        self.addAction(action_grid)

        action_rulers = QtGui.QAction("📏 Mostrar Réguas", self)
        action_rulers.setShortcut("Ctrl+Shift+R")
        action_rulers.setCheckable(True)
        action_rulers.triggered.connect(self.toggleRulersRequested.emit)
        self.addAction(action_rulers)
