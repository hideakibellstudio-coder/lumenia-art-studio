"""
MenuBar — Barra de Menus Principal Profissional da Lumenia UI
=============================================================
Estruturada no rigoroso padrão da indústria criativa:
  [Arquivo] [Editar] [Imagem] [Camada] [Seleção] [Filtros] [Exibir] [Janela] [Configurações] [Ajuda]
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore

from .file_menu import FileMenu
from .edit_menu import EditMenu
from .image_menu import ImageMenu
from .layer_menu import LayerMenu
from .select_menu import SelectMenu
from .filter_menu import FilterMenu
from .view_menu import ViewMenu
from .window_menu import WindowMenu
from .help_menu import HelpMenu
from .settings_menu import SettingsMenu
from ui.infrastructure.runtime_paths import resource_path


class MenuBar(QtWidgets.QMenuBar):
    # ── Arquivo ──────────────────────────────────────────────────────────
    newDocumentRequested    = QtCore.Signal()
    openDocumentRequested   = QtCore.Signal()
    saveDocumentRequested   = QtCore.Signal()
    saveAsDocumentRequested = QtCore.Signal()
    exportImageRequested    = QtCore.Signal()
    closeDocumentRequested  = QtCore.Signal()

    # ── Editar ───────────────────────────────────────────────────────────
    undoRequested           = QtCore.Signal()
    redoRequested           = QtCore.Signal()
    cutRequested            = QtCore.Signal()
    copyRequested           = QtCore.Signal()
    pasteRequested          = QtCore.Signal()
    fillRequested           = QtCore.Signal()
    clearLayerRequested     = QtCore.Signal()
    freeTransformRequested  = QtCore.Signal()

    # ── Imagem ───────────────────────────────────────────────────────────
    canvasSizeRequested       = QtCore.Signal()
    imageSizeRequested        = QtCore.Signal()
    cropRequested             = QtCore.Signal()
    rotate90CWRequested       = QtCore.Signal()
    rotate90CCWRequested      = QtCore.Signal()
    rotate180Requested        = QtCore.Signal()
    flipHorizontalRequested   = QtCore.Signal()
    flipVerticalRequested     = QtCore.Signal()
    brightnessContrastRequested = QtCore.Signal()
    hueSaturationRequested    = QtCore.Signal()
    invertColorsRequested     = QtCore.Signal()

    # ── Camada ───────────────────────────────────────────────────────────
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

    # ── Seleção ──────────────────────────────────────────────────────────
    selectAllRequested        = QtCore.Signal()
    deselectRequested         = QtCore.Signal()
    invertSelectionRequested  = QtCore.Signal()
    expandSelectionRequested  = QtCore.Signal()
    contractSelectionRequested = QtCore.Signal()
    featherSelectionRequested = QtCore.Signal()
    magicWandRequested        = QtCore.Signal()

    # ── Filtros ──────────────────────────────────────────────────────────
    filterGalleryRequested       = QtCore.Signal()
    gaussianBlurRequested        = QtCore.Signal()
    pixelateRequested            = QtCore.Signal()
    hueSaturationFilterRequested = QtCore.Signal()
    brightnessContrastFilterRequested = QtCore.Signal()
    colorBalanceFilterRequested  = QtCore.Signal()
    invertFilterRequested        = QtCore.Signal()

    # ── Exibir ───────────────────────────────────────────────────────────
    zoomInRequested         = QtCore.Signal()
    zoomOutRequested        = QtCore.Signal()
    resetViewRequested      = QtCore.Signal()
    fitToScreenRequested    = QtCore.Signal()
    resetRotationRequested  = QtCore.Signal()
    toggleGridRequested     = QtCore.Signal()
    toggleRulersRequested   = QtCore.Signal()
    telemetryGridRequested  = QtCore.Signal()
    toggleSoftProofRequested = QtCore.Signal(bool)
    toggleFullscreenRequested = QtCore.Signal()

    # ── Janela & Docks ───────────────────────────────────────────────────
    togglePanelRequested             = QtCore.Signal(str, str)  # panel_id, side
    collapseAllSidebarsRequested     = QtCore.Signal()
    expandAllSidebarsRequested       = QtCore.Signal()
    dockSettingsRequested            = QtCore.Signal()
    floatingToolbarSettingsRequested = QtCore.Signal()
    scaleRequested                   = QtCore.Signal(float)

    # ── 9. Configurações ──────────────────────────────────────────────────
    renderSettingsRequested   = QtCore.Signal()
    curvesLutRequested        = QtCore.Signal()
    cursorSettingsRequested   = QtCore.Signal()
    shortcutsRequested        = QtCore.Signal()
    themeSettingsRequested    = QtCore.Signal()
    managePluginsRequested    = QtCore.Signal()
    languageRequested         = QtCore.Signal(str)

    # ── 10. Ajuda ─────────────────────────────────────────────────────────
    userGuideRequested        = QtCore.Signal()
    testReportRequested       = QtCore.Signal()
    diagnosticsRequested      = QtCore.Signal()
    feedbackRequested         = QtCore.Signal()
    aboutRequested            = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_menus()
        from ui.infrastructure.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

    def setup_menus(self):
        # 0. [Logo Oficial / Branding Action]
        icon_path = resource_path("assets", "images", "icon_lumenia.png")
        if icon_path.is_file():
            act_brand = QtGui.QAction(QtGui.QIcon(str(icon_path)), "", self)
            act_brand.setToolTip("Lumenia 2.0 • Clique para Sobre o Software")
            act_brand.triggered.connect(self.aboutRequested.emit)
            self.addAction(act_brand)

        # 1. [Arquivo]
        self.file_menu = FileMenu(self)
        self.file_menu.newDocumentRequested.connect(self.newDocumentRequested.emit)
        self.file_menu.openDocumentRequested.connect(self.openDocumentRequested.emit)
        self.file_menu.saveDocumentRequested.connect(self.saveDocumentRequested.emit)
        self.file_menu.saveAsDocumentRequested.connect(self.saveAsDocumentRequested.emit)
        self.file_menu.exportImageRequested.connect(self.exportImageRequested.emit)
        self.file_menu.closeDocumentRequested.connect(self.closeDocumentRequested.emit)
        self.addMenu(self.file_menu)

        # 2. [Editar]
        self.edit_menu = EditMenu(self)
        self.edit_menu.undoRequested.connect(self.undoRequested.emit)
        self.edit_menu.redoRequested.connect(self.redoRequested.emit)
        self.edit_menu.cutRequested.connect(self.cutRequested.emit)
        self.edit_menu.copyRequested.connect(self.copyRequested.emit)
        self.edit_menu.pasteRequested.connect(self.pasteRequested.emit)
        self.edit_menu.fillRequested.connect(self.fillRequested.emit)
        self.edit_menu.clearLayerRequested.connect(self.clearLayerRequested.emit)
        self.edit_menu.freeTransformRequested.connect(self.freeTransformRequested.emit)
        self.addMenu(self.edit_menu)

        # 3. [Imagem]
        self.image_menu = ImageMenu(self)
        self.image_menu.canvasSizeRequested.connect(self.canvasSizeRequested.emit)
        self.image_menu.imageSizeRequested.connect(self.imageSizeRequested.emit)
        self.image_menu.cropRequested.connect(self.cropRequested.emit)
        self.image_menu.rotate90CWRequested.connect(self.rotate90CWRequested.emit)
        self.image_menu.rotate90CCWRequested.connect(self.rotate90CCWRequested.emit)
        self.image_menu.rotate180Requested.connect(self.rotate180Requested.emit)
        self.image_menu.flipHorizontalRequested.connect(self.flipHorizontalRequested.emit)
        self.image_menu.flipVerticalRequested.connect(self.flipVerticalRequested.emit)
        self.image_menu.brightnessContrastRequested.connect(self.brightnessContrastRequested.emit)
        self.image_menu.hueSaturationRequested.connect(self.hueSaturationRequested.emit)
        self.image_menu.invertColorsRequested.connect(self.invertColorsRequested.emit)
        self.addMenu(self.image_menu)

        # 4. [Camada]
        self.layer_menu = LayerMenu(self)
        self.layer_menu.newLayerRequested.connect(self.newLayerRequested.emit)
        self.layer_menu.newGroupRequested.connect(self.newGroupRequested.emit)
        self.layer_menu.duplicateLayerRequested.connect(self.duplicateLayerRequested.emit)
        self.layer_menu.deleteLayerRequested.connect(self.deleteLayerRequested.emit)
        self.layer_menu.mergeDownRequested.connect(self.mergeDownRequested.emit)
        self.layer_menu.flattenGroupRequested.connect(self.flattenGroupRequested.emit)
        self.layer_menu.flattenImageRequested.connect(self.flattenImageRequested.emit)
        self.layer_menu.toggleClippingRequested.connect(self.toggleClippingRequested.emit)
        self.layer_menu.toggleAlphaLockRequested.connect(self.toggleAlphaLockRequested.emit)
        self.layer_menu.toggleVisibilityRequested.connect(self.toggleVisibilityRequested.emit)
        self.layer_menu.layerPropertiesRequested.connect(self.layerPropertiesRequested.emit)
        self.addMenu(self.layer_menu)

        # 5. [Seleção]
        self.select_menu = SelectMenu(self)
        self.select_menu.selectAllRequested.connect(self.selectAllRequested.emit)
        self.select_menu.deselectRequested.connect(self.deselectRequested.emit)
        self.select_menu.invertSelectionRequested.connect(self.invertSelectionRequested.emit)
        self.select_menu.expandSelectionRequested.connect(self.expandSelectionRequested.emit)
        self.select_menu.contractSelectionRequested.connect(self.contractSelectionRequested.emit)
        self.select_menu.featherSelectionRequested.connect(self.featherSelectionRequested.emit)
        self.select_menu.magicWandRequested.connect(self.magicWandRequested.emit)
        self.addMenu(self.select_menu)

        # 6. [Filtros]
        self.filter_menu = FilterMenu(self)
        self.filter_menu.filterGalleryRequested.connect(self.filterGalleryRequested.emit)
        self.filter_menu.gaussianBlurRequested.connect(self.gaussianBlurRequested.emit)
        self.filter_menu.pixelateRequested.connect(self.pixelateRequested.emit)
        self.filter_menu.hueSaturationFilterRequested.connect(self.hueSaturationFilterRequested.emit)
        self.filter_menu.brightnessContrastFilterRequested.connect(self.brightnessContrastFilterRequested.emit)
        self.filter_menu.colorBalanceFilterRequested.connect(self.colorBalanceFilterRequested.emit)
        self.filter_menu.invertFilterRequested.connect(self.invertFilterRequested.emit)
        self.addMenu(self.filter_menu)

        # 7. [Exibir]
        self.view_menu = ViewMenu(self)
        self.view_menu.zoomInRequested.connect(self.zoomInRequested.emit)
        self.view_menu.zoomOutRequested.connect(self.zoomOutRequested.emit)
        self.view_menu.resetViewRequested.connect(self.resetViewRequested.emit)
        self.view_menu.fitToScreenRequested.connect(self.fitToScreenRequested.emit)
        self.view_menu.resetRotationRequested.connect(self.resetRotationRequested.emit)
        self.view_menu.toggleSoftProofRequested.connect(self.toggleSoftProofRequested.emit)
        self.view_menu.toggleGridRequested.connect(self.toggleGridRequested.emit)
        self.view_menu.toggleRulersRequested.connect(self.toggleRulersRequested.emit)
        self.view_menu.telemetryGridRequested.connect(self.telemetryGridRequested.emit)
        self.view_menu.toggleFullscreenRequested.connect(self.toggleFullscreenRequested.emit)
        self.addMenu(self.view_menu)

        # 8. [Janela]
        self.window_menu = WindowMenu(self)
        self.window_menu.toggle_panel_requested.connect(self.togglePanelRequested.emit)
        self.window_menu.collapse_all_sidebars_requested.connect(self.collapseAllSidebarsRequested.emit)
        self.window_menu.expand_all_sidebars_requested.connect(self.expandAllSidebarsRequested.emit)
        self.window_menu.dock_settings_requested.connect(self.dockSettingsRequested.emit)
        self.window_menu.floating_toolbar_settings_requested.connect(self.floatingToolbarSettingsRequested.emit)
        self.window_menu.telemetry_grid_requested.connect(self.telemetryGridRequested.emit)
        self.window_menu.scale_requested.connect(self.scaleRequested.emit)
        self.window_menu.toggle_fullscreen_requested.connect(self.toggleFullscreenRequested.emit)
        self.addMenu(self.window_menu)

        # 9. [Configurações]
        self.settings_menu = SettingsMenu(self)
        self.settings_menu.renderSettingsRequested.connect(self.renderSettingsRequested.emit)
        self.settings_menu.curvesLutRequested.connect(self.curvesLutRequested.emit)
        self.settings_menu.cursorSettingsRequested.connect(self.cursorSettingsRequested.emit)
        self.settings_menu.shortcutsRequested.connect(self.shortcutsRequested.emit)
        self.settings_menu.themeSettingsRequested.connect(self.themeSettingsRequested.emit)
        self.settings_menu.managePluginsRequested.connect(self.managePluginsRequested.emit)
        self.settings_menu.languageRequested.connect(self.languageRequested.emit)
        self.addMenu(self.settings_menu)

        # 10. [Ajuda]
        self.help_menu = HelpMenu(self)
        self.help_menu.shortcutsRequested.connect(self.shortcutsRequested.emit)
        self.help_menu.userGuideRequested.connect(self.userGuideRequested.emit)
        self.help_menu.testReportRequested.connect(self.testReportRequested.emit)
        self.help_menu.diagnosticsRequested.connect(self.diagnosticsRequested.emit)
        self.help_menu.feedbackRequested.connect(self.feedbackRequested.emit)
        self.help_menu.aboutRequested.connect(self.aboutRequested.emit)
        self.addMenu(self.help_menu)

    def retranslate_ui(self):
        for menu in (self.file_menu, self.edit_menu, self.image_menu, self.layer_menu, self.select_menu,
                     self.filter_menu, self.view_menu, self.window_menu, self.settings_menu, self.help_menu):
            menu.retranslate_ui()

    def update_history_state(self, can_undo: bool, can_redo: bool) -> None:
        """Propaga o estado de histórico para o menu Editar."""
        self.edit_menu.update_history_state(can_undo, can_redo)

    def set_panel_checked(self, panel_id: str, visible: bool) -> None:
        """Marca no menu Janela o painel que está aberto numa gaveta."""
        self.window_menu.set_panel_checked(panel_id, visible)
