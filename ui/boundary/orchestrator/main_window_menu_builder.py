"""Helper module to construct MenuBar and Keyboard Shortcuts for MainWindow."""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.components import MenuBar, ToolSidebar, StatusBar


def setup_menu_and_shortcuts(win: QtWidgets.QMainWindow) -> None:
    """Configura o MenuBar, ToolSidebar, StatusBar e atalhos de teclado globais."""
    # ── Menu Bar ──────────────────────────────────────────────────────
    win.menu_bar = MenuBar(win)
    win.setMenuBar(win.menu_bar)

    # Arquivo
    win.menu_bar.newDocumentRequested.connect(win.open_new_document_dialog)
    win.menu_bar.openDocumentRequested.connect(win.open_image_file)
    win.menu_bar.saveDocumentRequested.connect(win.save_active_document)
    win.menu_bar.saveAsDocumentRequested.connect(win.export_image)
    win.menu_bar.exportImageRequested.connect(win.export_image)
    win.menu_bar.closeDocumentRequested.connect(win.close_active_document)
    win.menu_bar.clearCanvasRequested.connect(win.clear_screen)

    # Editar
    win.menu_bar.undoRequested.connect(win.undo)
    win.menu_bar.redoRequested.connect(win.redo)
    win.menu_bar.clearLayerRequested.connect(win.clear_screen)
    win.menu_bar.freeTransformRequested.connect(lambda: win.select_tool_by_id("transform"))
    win.menu_bar.preferencesRequested.connect(win.open_render_settings_dialog)

    # Imagem & Rotações
    win.menu_bar.resetRotationRequested.connect(win.reset_rotation)
    win.menu_bar.flipHorizontalRequested.connect(win.flip_horizontal)
    win.menu_bar.flipVerticalRequested.connect(win.flip_vertical)

    # Camadas & Grupos
    win.menu_bar.newLayerRequested.connect(win.create_new_layer)
    win.menu_bar.newGroupRequested.connect(win.create_new_group)
    win.menu_bar.duplicateLayerRequested.connect(win.duplicate_active_layer)
    win.menu_bar.deleteLayerRequested.connect(win.delete_active_layer)
    win.menu_bar.mergeDownRequested.connect(win.merge_layer_down)

    # Filtros
    win.menu_bar.filterGalleryRequested.connect(win.open_filter_gallery)

    # Exibir
    win.menu_bar.zoomInRequested.connect(win.zoom_in)
    win.menu_bar.zoomOutRequested.connect(win.zoom_out)
    win.menu_bar.resetViewRequested.connect(win.reset_view)
    win.menu_bar.fitToScreenRequested.connect(win.reset_view)
    win.menu_bar.renderSettingsRequested.connect(win.open_render_settings_dialog)

    # Janela & Docks
    win.menu_bar.dockSettingsRequested.connect(win.open_dock_settings_dialog)

    # Configurações & Temas
    win.menu_bar.curvesLutRequested.connect(win.open_curve_window)
    win.menu_bar.themeSettingsRequested.connect(win.open_theme_dialog)
    win.menu_bar.managePluginsRequested.connect(win.open_plugins_dialog)

    # Ajuda
    win.menu_bar.shortcutsRequested.connect(win.open_shortcuts_dialog)
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
    win.tool_sidebar.clearRequested.connect(win.clear_screen)
    win.tool_sidebar.deselectRequested.connect(win.deselect_selection)

    # ── Atalhos de Teclado Globais ────────────────────────────────────
    win.shortcut_undo = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Z"), win)
    win.shortcut_undo.activated.connect(win.undo)

    win.shortcut_redo_y = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Y"), win)
    win.shortcut_redo_y.activated.connect(win.redo)

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

    # ── Status Bar ────────────────────────────────────────────────────
    win.status_bar = StatusBar(win)
    win.setStatusBar(win.status_bar)
