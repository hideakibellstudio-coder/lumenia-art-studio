"""
ViewMenu — Menu Exibir (Padrão Profissional da Indústria)
=========================================================
Expõe controles de Zoom, Ajuste à Tela, Reset de Câmera, Prova de Cores e Guias do Canvas.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon


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
        action_zoom_in = QtGui.QAction(get_icon("zoom_in"), "Aproximar (Zoom In)", self)
        action_zoom_in.setShortcut("Ctrl+=")
        action_zoom_in.triggered.connect(self.zoomInRequested.emit)
        self.addAction(action_zoom_in)

        action_zoom_out = QtGui.QAction(get_icon("zoom_out"), "Afastar (Zoom Out)", self)
        action_zoom_out.setShortcut("Ctrl+-")
        action_zoom_out.triggered.connect(self.zoomOutRequested.emit)
        self.addAction(action_zoom_out)

        self.addSeparator()

        # 2. Enquadramento e Câmera
        action_reset = QtGui.QAction(get_icon("display"), "Zoom 100% (Tamanho Real)", self)
        action_reset.setShortcut("Ctrl+0")
        action_reset.triggered.connect(self.resetViewRequested.emit)
        self.addAction(action_reset)

        action_fit = QtGui.QAction(get_icon("display"), "Ajustar à Tela", self)
        action_fit.setShortcut("Ctrl+Alt+0")
        action_fit.triggered.connect(self.fitToScreenRequested.emit)
        self.addAction(action_fit)

        action_reset_rot = QtGui.QAction(get_icon("reset"), "Resetar Rotação e Ângulo", self)
        action_reset_rot.setShortcut("Ctrl+R")
        action_reset_rot.triggered.connect(self.resetRotationRequested.emit)
        self.addAction(action_reset_rot)

        self.addSeparator()

        # 3. Prova de Cores & Renderização
        action_proof = QtGui.QAction(get_icon("proof"), "Prova de Cores & Renderização...", self)
        action_proof.triggered.connect(self.renderSettingsRequested.emit)
        self.addAction(action_proof)

        self.addSeparator()

        # 4. Guias & Réguas
        self.action_grid = QtGui.QAction(get_icon("grid"), "Exibir Grade Magnética (Grid)", self)
        self.action_grid.setCheckable(True)
        self.action_grid.setShortcut("Ctrl+'")
        self.action_grid.triggered.connect(self.toggleGridRequested.emit)
        self.addAction(self.action_grid)

        self.action_rulers = QtGui.QAction(get_icon("ruler"), "Exibir Réguas", self)
        self.action_rulers.setCheckable(True)
        self.action_rulers.setShortcut("Ctrl+R")
        self.action_rulers.triggered.connect(self.toggleRulersRequested.emit)
        self.addAction(self.action_rulers)
