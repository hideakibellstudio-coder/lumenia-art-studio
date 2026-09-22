"""
ViewMenu — Menu Exibir (Padrão Profissional da Indústria) — ARCcC i18n.
========================================================================
Expõe controles de Zoom, Ajuste à Tela, Reset de Câmera, Prova de Cores e Guias do Canvas.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon
from ui.core.i18n import tr


class ViewMenu(QtWidgets.QMenu):
    zoomInRequested        = QtCore.Signal()
    zoomOutRequested       = QtCore.Signal()
    resetViewRequested     = QtCore.Signal()
    fitToScreenRequested   = QtCore.Signal()
    resetRotationRequested = QtCore.Signal()
    toggleSoftProofRequested = QtCore.Signal(bool)
    toggleGridRequested    = QtCore.Signal()
    toggleRulersRequested  = QtCore.Signal()
    toggleFullscreenRequested = QtCore.Signal()
    telemetryGridRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Exibir", parent)
        self.setup_actions()
        self.retranslate_ui()

    def setup_actions(self):
        # 1. Controles de Zoom
        self.action_zoom_in = QtGui.QAction(get_icon("zoom_in"), "", self)
        self.action_zoom_in.setShortcut("Ctrl+=")
        self.action_zoom_in.triggered.connect(self.zoomInRequested.emit)
        self.addAction(self.action_zoom_in)

        self.action_zoom_out = QtGui.QAction(get_icon("zoom_out"), "", self)
        self.action_zoom_out.setShortcut("Ctrl+-")
        self.action_zoom_out.triggered.connect(self.zoomOutRequested.emit)
        self.addAction(self.action_zoom_out)

        self.addSeparator()

        # 2. Enquadramento e Câmera
        self.action_reset = QtGui.QAction(get_icon("display"), "", self)
        self.action_reset.setShortcut("Ctrl+0")
        self.action_reset.triggered.connect(self.resetViewRequested.emit)
        self.addAction(self.action_reset)

        self.action_fit = QtGui.QAction(get_icon("display"), "", self)
        self.action_fit.setShortcut("Ctrl+Alt+0")
        self.action_fit.triggered.connect(self.fitToScreenRequested.emit)
        self.addAction(self.action_fit)

        self.action_reset_rot = QtGui.QAction(get_icon("reset"), "", self)
        self.action_reset_rot.setShortcut("Ctrl+R")
        self.action_reset_rot.triggered.connect(self.resetRotationRequested.emit)
        self.addAction(self.action_reset_rot)

        self.addSeparator()

        # 3. Prova de Cores (toggle leve -- liga/desliga soft-proofing direto
        #    no backend, sem abrir o RenderSettingsDialog. O dialogo completo
        #    de configuracao de perfil/intent continua em Configuracoes >
        #    Renderizacao & Modos de Cor).
        self.action_proof = QtGui.QAction(get_icon("proof"), "", self)
        self.action_proof.setCheckable(True)
        self.action_proof.toggled.connect(self.toggleSoftProofRequested.emit)
        self.addAction(self.action_proof)

        self.addSeparator()

        # 4. Guias & Réguas
        self.action_grid = QtGui.QAction(get_icon("grid"), "", self)
        self.action_grid.setCheckable(True)
        self.action_grid.setShortcut("Ctrl+'")
        self.action_grid.triggered.connect(self.toggleGridRequested.emit)
        self.addAction(self.action_grid)

        self.action_rulers = QtGui.QAction(get_icon("ruler"), "", self)
        self.action_rulers.setCheckable(True)
        self.action_rulers.setShortcut("Ctrl+Shift+R")
        self.action_rulers.triggered.connect(self.toggleRulersRequested.emit)
        self.addAction(self.action_rulers)

        self.addSeparator()

        # 5. Modo Tela Cheia
        self.action_fullscreen = QtGui.QAction(get_icon("fullscreen"), "", self)
        self.action_fullscreen.setCheckable(True)
        self.action_fullscreen.setShortcut("F11")
        self.action_fullscreen.triggered.connect(self.toggleFullscreenRequested.emit)
        self.addAction(self.action_fullscreen)

        self.addSeparator()

        # 6. Diagnóstico & Telemetria em Grid
        self.action_telemetry_grid = QtGui.QAction(get_icon("chart"), "", self)
        self.action_telemetry_grid.setShortcut("F12")
        self.action_telemetry_grid.triggered.connect(self.telemetryGridRequested.emit)
        self.addAction(self.action_telemetry_grid)

    def retranslate_ui(self):
        self.setTitle(tr("menu.view.title", "Exibir"))
        self.action_zoom_in.setText(tr("menu.view.zoom_in", "Aproximar Zoom"))
        self.action_zoom_out.setText(tr("menu.view.zoom_out", "Afastar Zoom"))
        self.action_reset.setText(tr("menu.view.zoom_100", "Pixels Reais (100%)"))
        self.action_fit.setText(tr("menu.view.fit_to_screen", "Ajustar à Tela"))
        self.action_reset_rot.setText(tr("menu.view.reset_view", "Resetar Vista e Rotação"))
        self.action_proof.setText(tr("menu.view.soft_proof_toggle", "Prova de Cores (Ativar/Desativar)"))
        self.action_grid.setText(tr("menu.view.toggle_grid", "Alternar Grade Guia"))
        self.action_rulers.setText(tr("menu.view.toggle_rulers", "Alternar Réguas"))
        self.action_fullscreen.setText(tr("menu.view.fullscreen", "Modo Tela Cheia"))
        self.action_telemetry_grid.setText(tr("menu.view.telemetry_grid", "Cockpit de Telemetria (Grid)..."))
