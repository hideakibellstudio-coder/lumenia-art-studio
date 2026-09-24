"""Liga os sinais da MenuBar e da ToolSidebar aos colaboradores da janela principal.

Só conecta sinais: não cria widgets nem pendura atributos em ninguém (até
2026-09-24 `setup_menu_and_shortcuts(win)` criava `win.menu_bar`,
`win.status_bar`, `win.shortcut_*`...). Quem cria os componentes é a
`MainWindow`; quem executa cada ação é o colaborador indicado.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ui.core.components import MenuBar, ToolSidebar

from .dialog_actions import DialogActions
from .document_actions import DocumentActions
from .edit_actions import EditActions
from .image_actions import ImageActions
from .layer_actions import LayerActions

if TYPE_CHECKING:  # só tipagem: evita ciclo de import
    from .main_window import MainWindow


@dataclass(frozen=True)
class ShellCollaborators:
    documents: DocumentActions
    edit: EditActions
    layers: LayerActions
    image: ImageActions
    dialogs: DialogActions


def wire_menu_bar(menu: MenuBar, shell: "MainWindow", c: ShellCollaborators) -> None:
    docs, edit, image, dialogs = c.documents, c.edit, c.image, c.dialogs
    layers = c.layers.commands

    # 1. Arquivo
    menu.newDocumentRequested.connect(docs.new_document)
    menu.openDocumentRequested.connect(docs.open_file)
    menu.saveDocumentRequested.connect(docs.save_active)
    menu.saveAsDocumentRequested.connect(docs.save_active_as)
    menu.exportImageRequested.connect(image.export_image)
    menu.closeDocumentRequested.connect(docs.close_active)

    # 2. Editar
    menu.undoRequested.connect(shell.undo)
    menu.redoRequested.connect(shell.redo)
    menu.edit_menu.aboutToShow.connect(shell.update_undo_redo_actions)
    menu.cutRequested.connect(edit.cut)
    menu.copyRequested.connect(edit.copy)
    menu.pasteRequested.connect(edit.paste)
    menu.fillRequested.connect(edit.fill)
    menu.clearLayerRequested.connect(layers.clear_active_pixels)
    menu.freeTransformRequested.connect(lambda: shell.select_tool_by_id("transform"))

    # 3. Imagem
    menu.canvasSizeRequested.connect(lambda: image.resize_dialog(False))
    menu.imageSizeRequested.connect(lambda: image.resize_dialog(True))
    menu.cropRequested.connect(image.crop_to_selection)
    menu.rotate90CWRequested.connect(lambda: image.rotate_layer_90(True))
    menu.rotate90CCWRequested.connect(lambda: image.rotate_layer_90(False))
    menu.rotate180Requested.connect(image.rotate_layer_180)
    menu.resetRotationRequested.connect(image.reset_view_rotation)
    menu.flipHorizontalRequested.connect(image.flip_view_horizontal)
    menu.flipVerticalRequested.connect(image.flip_view_vertical)
    menu.brightnessContrastRequested.connect(lambda: dialogs.open_filter_dialog("brightness"))
    menu.hueSaturationRequested.connect(lambda: dialogs.open_filter_dialog("huesat"))
    menu.invertColorsRequested.connect(lambda: dialogs.open_filter_dialog("invert"))

    # 4. Camadas
    menu.newLayerRequested.connect(lambda: layers.add_layer())
    menu.newGroupRequested.connect(lambda: layers.add_group())
    menu.duplicateLayerRequested.connect(layers.duplicate_active)
    menu.deleteLayerRequested.connect(layers.delete_active)
    menu.mergeDownRequested.connect(layers.merge_active_down)
    menu.flattenGroupRequested.connect(layers.flatten_active_group)
    menu.flattenImageRequested.connect(layers.flatten_image)
    menu.toggleClippingRequested.connect(c.layers.toggle_active_clipping)
    menu.toggleAlphaLockRequested.connect(c.layers.toggle_active_alpha_lock)
    menu.toggleVisibilityRequested.connect(c.layers.toggle_active_visibility)
    menu.layerPropertiesRequested.connect(c.layers.open_properties_dialog)

    # 5. Seleção
    menu.selectAllRequested.connect(edit.select_all)
    menu.deselectRequested.connect(edit.deselect)
    menu.invertSelectionRequested.connect(edit.invert_selection)
    menu.expandSelectionRequested.connect(lambda: edit.modify_selection("expand"))
    menu.contractSelectionRequested.connect(lambda: edit.modify_selection("contract"))
    menu.featherSelectionRequested.connect(lambda: edit.modify_selection("feather"))
    menu.magicWandRequested.connect(lambda: shell.select_tool_by_id("wand"))

    # 6. Filtros
    menu.filterGalleryRequested.connect(lambda: dialogs.open_filter_dialog())
    menu.gaussianBlurRequested.connect(lambda: dialogs.open_filter_dialog("blur"))
    menu.pixelateRequested.connect(lambda: dialogs.open_filter_dialog("pixelate"))
    menu.hueSaturationFilterRequested.connect(lambda: dialogs.open_filter_dialog("huesat"))
    menu.brightnessContrastFilterRequested.connect(lambda: dialogs.open_filter_dialog("brightness"))
    menu.colorBalanceFilterRequested.connect(lambda: dialogs.open_filter_dialog("colorbalance"))
    menu.invertFilterRequested.connect(lambda: dialogs.open_filter_dialog("invert"))

    # 7. Exibir
    menu.zoomInRequested.connect(shell.zoom_in)
    menu.zoomOutRequested.connect(shell.zoom_out)
    menu.resetViewRequested.connect(shell.reset_view)
    menu.fitToScreenRequested.connect(shell.reset_view)
    menu.renderSettingsRequested.connect(dialogs.open_render_settings)
    menu.toggleSoftProofRequested.connect(image.toggle_soft_proof)
    menu.toggleGridRequested.connect(image.toggle_grid)
    menu.toggleRulersRequested.connect(image.toggle_rulers)
    menu.telemetryGridRequested.connect(dialogs.open_telemetry_window)
    menu.toggleFullscreenRequested.connect(shell.toggle_fullscreen)

    # 8. Janela e docas
    menu.dockSettingsRequested.connect(dialogs.open_dock_settings)
    menu.floatingToolbarSettingsRequested.connect(dialogs.open_floating_toolbar_settings)
    menu.scaleRequested.connect(dialogs.set_interface_scale)

    # 9. Configurações
    menu.curvesLutRequested.connect(dialogs.open_curve_window)
    menu.cursorSettingsRequested.connect(dialogs.open_cursor_settings)
    menu.themeSettingsRequested.connect(dialogs.open_theme_dialog)
    menu.managePluginsRequested.connect(dialogs.open_plugins_dialog)
    menu.languageRequested.connect(dialogs.set_language)

    # 10. Ajuda
    menu.shortcutsRequested.connect(dialogs.open_shortcuts)
    menu.userGuideRequested.connect(dialogs.open_user_guide)
    menu.testReportRequested.connect(dialogs.open_test_report)
    menu.diagnosticsRequested.connect(dialogs.open_diagnostics)
    menu.feedbackRequested.connect(dialogs.open_feedback_form)
    menu.aboutRequested.connect(dialogs.open_about)


def wire_tool_sidebar(sidebar: ToolSidebar, shell: "MainWindow", c: ShellCollaborators) -> None:
    sidebar.brushSelected.connect(lambda: shell.select_tool_by_id("brush"))
    sidebar.eraserSelected.connect(lambda: shell.select_tool_by_id("eraser"))
    sidebar.shapesSelected.connect(lambda: shell.select_tool_by_id("shapes"))
    sidebar.undoRequested.connect(shell.undo)
    sidebar.redoRequested.connect(shell.redo)
    sidebar.zoomInRequested.connect(shell.zoom_in)
    sidebar.zoomOutRequested.connect(shell.zoom_out)
    sidebar.resetRequested.connect(shell.reset_view)
    sidebar.clearRequested.connect(c.layers.commands.clear_active_pixels)
    sidebar.deselectRequested.connect(c.edit.deselect)
