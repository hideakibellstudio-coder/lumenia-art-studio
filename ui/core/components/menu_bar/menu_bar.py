"""
MenuBar — Barra de Menus Principal da Lumenia UI
===============================================
Encapsula os menus Arquivo, Exibir, Janela, Tema, Plugins e Configurações / Curvas LUT.
"""

from PySide6 import QtWidgets, QtGui, QtCore
from .file_menu import FileMenu
from .view_menu import ViewMenu
from .theme_menu import ThemeMenu
from .plugins_menu import PluginsMenu
from .window_menu import WindowMenu


class MenuBar(QtWidgets.QMenuBar):
    newDocumentRequested    = QtCore.Signal()
    closeDocumentRequested  = QtCore.Signal()
    exportImageRequested    = QtCore.Signal()
    clearCanvasRequested    = QtCore.Signal()

    zoomInRequested         = QtCore.Signal()
    zoomOutRequested        = QtCore.Signal()
    resetViewRequested      = QtCore.Signal()
    resetRotationRequested  = QtCore.Signal()

    themeSettingsRequested  = QtCore.Signal()
    managePluginsRequested  = QtCore.Signal()
    curvesLutRequested      = QtCore.Signal()

    # Sinais do menu Janela
    togglePanelRequested             = QtCore.Signal(str, str)  # panel_id, side
    collapseAllSidebarsRequested     = QtCore.Signal()
    expandAllSidebarsRequested       = QtCore.Signal()
    dockSettingsRequested            = QtCore.Signal()
    floatingToolbarSettingsRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_menus()

    def setup_menus(self):
        # 1. Arquivo
        self.file_menu = FileMenu(self)
        self.file_menu.newDocumentRequested.connect(self.newDocumentRequested.emit)
        self.file_menu.closeDocumentRequested.connect(self.closeDocumentRequested.emit)
        self.file_menu.exportImageRequested.connect(self.exportImageRequested.emit)
        self.file_menu.clearCanvasRequested.connect(self.clearCanvasRequested.emit)
        self.addMenu(self.file_menu)

        # 2. Exibir (antigo Visualizar)
        self.view_menu = ViewMenu(self)
        self.view_menu.zoomInRequested.connect(self.zoomInRequested.emit)
        self.view_menu.zoomOutRequested.connect(self.zoomOutRequested.emit)
        self.view_menu.resetViewRequested.connect(self.resetViewRequested.emit)
        self.view_menu.resetRotationRequested.connect(self.resetRotationRequested.emit)
        self.addMenu(self.view_menu)

        # 3. Janela
        self.window_menu = WindowMenu(self)
        self.window_menu.toggle_panel_requested.connect(self.togglePanelRequested.emit)
        self.window_menu.collapse_all_sidebars_requested.connect(self.collapseAllSidebarsRequested.emit)
        self.window_menu.expand_all_sidebars_requested.connect(self.expandAllSidebarsRequested.emit)
        self.window_menu.dock_settings_requested.connect(self.dockSettingsRequested.emit)
        self.window_menu.floating_toolbar_settings_requested.connect(self.floatingToolbarSettingsRequested.emit)
        self.addMenu(self.window_menu)

        # 4. Configurações / Curvas LUT
        self.settings_menu = QtWidgets.QMenu("Configurações", self)
        act_curves = QtGui.QAction("⚙ Curvas LUT (Perfis de Pincel)...", self)
        act_curves.triggered.connect(self.curvesLutRequested.emit)
        self.settings_menu.addAction(act_curves)
        self.addMenu(self.settings_menu)

        # 5. Tema
        self.theme_menu = ThemeMenu(self)
        self.theme_menu.themeSettingsRequested.connect(self.themeSettingsRequested.emit)
        self.addMenu(self.theme_menu)

        # 6. Plugins
        self.plugins_menu = PluginsMenu(self)
        self.plugins_menu.managePluginsRequested.connect(self.managePluginsRequested.emit)
        self.addMenu(self.plugins_menu)
