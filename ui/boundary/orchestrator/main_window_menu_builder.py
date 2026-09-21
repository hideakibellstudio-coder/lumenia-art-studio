"""Helper module to construct MenuBar and Keyboard Shortcuts for MainWindow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.components import MenuBar, ToolSidebar, StatusBar

if TYPE_CHECKING:  # apenas para tipagem: evita ciclo de import em runtime
    from .main_window import MainWindow


def setup_menu_and_shortcuts(win: MainWindow) -> None:
    """Configura o MenuBar, ToolSidebar, StatusBar e atalhos de teclado globais."""
    # ── Menu Bar ──────────────────────────────────────────────────────
    win.menu_bar = MenuBar(win)
    win.setMenuBar(win.menu_bar)

    # 1. Arquivo
    win.menu_bar.newDocumentRequested.connect(win.open_new_document_dialog)
    win.menu_bar.openDocumentRequested.connect(win.open_image_file)
    win.menu_bar.saveDocumentRequested.connect(win.save_active_document)
    win.menu_bar.saveAsDocumentRequested.connect(win.save_active_document_as)
    win.menu_bar.exportImageRequested.connect(win.export_image)
    win.menu_bar.closeDocumentRequested.connect(win.close_active_document)

    # 2. Editar
    win.menu_bar.undoRequested.connect(win.undo)
    win.menu_bar.redoRequested.connect(win.redo)
    if hasattr(win.menu_bar, "edit_menu") and win.menu_bar.edit_menu:
        win.menu_bar.edit_menu.aboutToShow.connect(win.update_undo_redo_actions)
    win.menu_bar.cutRequested.connect(win.cut_selection_or_layer_to_clipboard)
    win.menu_bar.copyRequested.connect(win.copy_selection_or_layer_to_clipboard)
    win.menu_bar.pasteRequested.connect(win.paste_clipboard)
    win.menu_bar.fillRequested.connect(win.fill_active_selection_or_canvas)
    win.menu_bar.clearLayerRequested.connect(win.clear_active_layer)
    win.menu_bar.freeTransformRequested.connect(lambda: win.select_tool_by_id("transform"))

    # 3. Imagem & Rotações
    win.menu_bar.canvasSizeRequested.connect(lambda: win.open_canvas_size_dialog(False))
    win.menu_bar.imageSizeRequested.connect(lambda: win.open_canvas_size_dialog(True))
    win.menu_bar.cropRequested.connect(win.crop_to_selection)
    win.menu_bar.rotate90CWRequested.connect(lambda: win.rotate_active_layer_90(True))
    win.menu_bar.rotate90CCWRequested.connect(lambda: win.rotate_active_layer_90(False))
    win.menu_bar.rotate180Requested.connect(win.rotate_active_layer_180)
    win.menu_bar.resetRotationRequested.connect(win.reset_rotation)
    win.menu_bar.flipHorizontalRequested.connect(win.flip_horizontal)
    win.menu_bar.flipVerticalRequested.connect(win.flip_vertical)
    win.menu_bar.brightnessContrastRequested.connect(lambda: win.open_filter_dialog("brightness"))
    win.menu_bar.hueSaturationRequested.connect(lambda: win.open_filter_dialog("huesat"))
    win.menu_bar.invertColorsRequested.connect(lambda: win.open_filter_dialog("invert"))

    # 4. Camadas & Grupos
    win.menu_bar.newLayerRequested.connect(win.create_new_layer)
    win.menu_bar.newGroupRequested.connect(win.create_new_group)
    win.menu_bar.duplicateLayerRequested.connect(win.duplicate_active_layer)
    win.menu_bar.deleteLayerRequested.connect(win.delete_active_layer)
    win.menu_bar.mergeDownRequested.connect(win.merge_layer_down)
    win.menu_bar.flattenGroupRequested.connect(win.flatten_active_group)
    win.menu_bar.flattenImageRequested.connect(win.flatten_entire_image)
    win.menu_bar.toggleClippingRequested.connect(win.toggle_active_layer_clipping)
    win.menu_bar.toggleAlphaLockRequested.connect(win.toggle_active_layer_alpha_lock)
    win.menu_bar.toggleVisibilityRequested.connect(win.toggle_active_layer_visibility)
    win.menu_bar.layerPropertiesRequested.connect(win.open_layer_properties_dialog)

    # 5. Seleção
    win.menu_bar.selectAllRequested.connect(win.select_all)
    win.menu_bar.deselectRequested.connect(win.deselect_selection)
    win.menu_bar.invertSelectionRequested.connect(win.invert_selection)
    win.menu_bar.expandSelectionRequested.connect(lambda: win.open_modify_selection_dialog("expand"))
    win.menu_bar.contractSelectionRequested.connect(lambda: win.open_modify_selection_dialog("contract"))
    win.menu_bar.featherSelectionRequested.connect(lambda: win.open_modify_selection_dialog("feather"))
    win.menu_bar.magicWandRequested.connect(lambda: win.select_tool_by_id("wand"))

    # 6. Filtros
    win.menu_bar.filterGalleryRequested.connect(win.open_filter_gallery)
    win.menu_bar.gaussianBlurRequested.connect(lambda: win.open_filter_dialog("blur"))
    win.menu_bar.pixelateRequested.connect(lambda: win.open_filter_dialog("pixelate"))
    win.menu_bar.hueSaturationFilterRequested.connect(lambda: win.open_filter_dialog("huesat"))
    win.menu_bar.brightnessContrastFilterRequested.connect(lambda: win.open_filter_dialog("brightness"))
    win.menu_bar.colorBalanceFilterRequested.connect(lambda: win.open_filter_dialog("colorbalance"))
    win.menu_bar.invertFilterRequested.connect(lambda: win.open_filter_dialog("invert"))

    # 7. Exibir
    win.menu_bar.zoomInRequested.connect(win.zoom_in)
    win.menu_bar.zoomOutRequested.connect(win.zoom_out)
    win.menu_bar.resetViewRequested.connect(win.reset_view)
    win.menu_bar.fitToScreenRequested.connect(win.reset_view)
    win.menu_bar.renderSettingsRequested.connect(win.open_render_settings_dialog)
    win.menu_bar.toggleSoftProofRequested.connect(win.toggle_soft_proof)
    win.menu_bar.toggleGridRequested.connect(win.toggle_grid)
    win.menu_bar.toggleRulersRequested.connect(win.toggle_rulers)
    win.menu_bar.telemetryGridRequested.connect(win.open_telemetry_grid_window)

    # 8. Janela & Docks
    win.menu_bar.dockSettingsRequested.connect(win.open_dock_settings_dialog)

    # 9. Configurações & Temas
    win.menu_bar.curvesLutRequested.connect(win.open_curve_window)
    win.menu_bar.cursorSettingsRequested.connect(win.open_cursor_settings_dialog)
    win.menu_bar.themeSettingsRequested.connect(win.open_theme_dialog)
    win.menu_bar.managePluginsRequested.connect(win.open_plugins_dialog)
    win.menu_bar.languageRequested.connect(win.set_application_language)

    # 10. Ajuda
    win.menu_bar.shortcutsRequested.connect(win.open_shortcuts_dialog)
    win.menu_bar.userGuideRequested.connect(win.open_user_guide)
    win.menu_bar.testReportRequested.connect(win.open_test_report_dialog)
    win.menu_bar.diagnosticsRequested.connect(win.open_diagnostics_dialog)
    win.menu_bar.feedbackRequested.connect(win.open_feedback_form)
    win.menu_bar.aboutRequested.connect(win.open_about_dialog)

    # ── Tool Sidebar ──────────────────────────────────────────────────
    win.tool_sidebar = ToolSidebar(win)
    win.addToolBar(QtCore.Qt.TopToolBarArea, win.tool_sidebar)
    win.tool_sidebar.brushSelected.connect(win.select_brush_tool)
    win.tool_sidebar.eraserSelected.connect(win.select_eraser_tool)
    win.tool_sidebar.shapesSelected.connect(win.select_shapes_tool)
    win.tool_sidebar.undoRequested.connect(win.undo)
    win.tool_sidebar.redoRequested.connect(win.redo)
    win.tool_sidebar.zoomInRequested.connect(win.zoom_in)
    win.tool_sidebar.zoomOutRequested.connect(win.zoom_out)
    win.tool_sidebar.resetRequested.connect(win.reset_view)
    win.tool_sidebar.clearRequested.connect(win.clear_active_layer)
    win.tool_sidebar.deselectRequested.connect(win.deselect_selection)

    # ── Atalhos de Teclado Globais ────────────────────────────────────
    # NOTA: Ctrl+Z e Ctrl+Y estão definidos nos QActions do EditMenu.
    # Apenas Ctrl+Shift+Z (alternativo de Redo) e atalhos de ferramentas
    # são criados como QShortcut global para evitar conflito de ambiguidade.
    win.shortcut_undo = win.menu_bar.edit_menu.act_undo
    win.shortcut_redo_y = win.menu_bar.edit_menu.act_redo

    win.shortcut_redo_shift_z = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+Z"), win)
    win.shortcut_redo_shift_z.activated.connect(win.redo)

    win.shortcut_tool_b = QtGui.QShortcut(QtGui.QKeySequence("B"), win)
    win.shortcut_tool_b.activated.connect(win.select_brush_tool)

    win.shortcut_tool_e = QtGui.QShortcut(QtGui.QKeySequence("E"), win)
    win.shortcut_tool_e.activated.connect(win.select_eraser_tool)

    win.shortcut_tool_u = QtGui.QShortcut(QtGui.QKeySequence("U"), win)
    win.shortcut_tool_u.activated.connect(win.select_shapes_tool)

    win.shortcut_tool_t = QtGui.QShortcut(QtGui.QKeySequence("T"), win)
    win.shortcut_tool_t.activated.connect(win.select_text_tool)

    win.shortcut_telemetry_f12 = win.menu_bar.view_menu.action_telemetry_grid

    # ── Status Bar ────────────────────────────────────────────────────
    win.status_bar = StatusBar(win)
    win.setStatusBar(win.status_bar)
