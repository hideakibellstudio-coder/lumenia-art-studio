"""Test Menu Bar Complete Wiring & Dialogs — Validação de Todas as Ações do Menu."""

import unittest
import sys
import os

from PySide6 import QtCore, QtGui, QtWidgets
from ui.boundary.orchestrator.main_window import MainWindow

# Assegura que QApplication existe em modo offscreen
app = QtWidgets.QApplication.instance()
if app is None:
    app = QtWidgets.QApplication(["--platform", "offscreen"])


class TestMenuBarCompleteWiring(unittest.TestCase):
    """Suíte de testes de integração para todos os menus e ações do MenuBar."""

    @classmethod
    def setUpClass(cls):
        top_mws = [w for w in QtWidgets.QApplication.topLevelWidgets() if isinstance(w, MainWindow)]
        if top_mws:
            cls.win = top_mws[0]
        else:
            cls.win = MainWindow()

    def setUp(self):
        pass

    def test_01_menu_bar_submenus_exist(self):
        """Verifica se todos os 10 submenus estão instanciados no menu_bar."""
        mb = self.win.menu_bar
        self.assertIsNotNone(mb.file_menu)
        self.assertIsNotNone(mb.edit_menu)
        self.assertIsNotNone(mb.image_menu)
        self.assertIsNotNone(mb.layer_menu)
        self.assertIsNotNone(mb.select_menu)
        self.assertIsNotNone(mb.filter_menu)
        self.assertIsNotNone(mb.view_menu)
        self.assertIsNotNone(mb.window_menu)
        self.assertIsNotNone(mb.settings_menu)
        self.assertIsNotNone(mb.help_menu)

    def test_02_file_menu_actions(self):
        """Testa acionamento das ações de Arquivo."""
        self.win.menu_bar.clearCanvasRequested.emit()
        self.win.menu_bar.saveDocumentRequested.emit()

    def test_03_edit_and_clipboard_actions(self):
        """Testa acionamento das ações de Edição e Área de Transferência."""
        self.win.menu_bar.undoRequested.emit()
        self.win.menu_bar.redoRequested.emit()
        self.win.menu_bar.copyRequested.emit()
        self.win.menu_bar.cutRequested.emit()
        self.win.menu_bar.fillRequested.emit()

    def test_04_selection_actions(self):
        """Testa acionamento das ações de Seleção."""
        self.win.menu_bar.selectAllRequested.emit()
        self.win.menu_bar.invertSelectionRequested.emit()
        self.win.menu_bar.deselectRequested.emit()
        self.win.menu_bar.magicWandRequested.emit()

    def test_05_layer_actions(self):
        """Testa acionamento das ações de Camadas."""
        self.win.menu_bar.newLayerRequested.emit()
        self.win.menu_bar.newGroupRequested.emit()
        self.win.menu_bar.toggleClippingRequested.emit()
        self.win.menu_bar.toggleAlphaLockRequested.emit()
        self.win.menu_bar.toggleVisibilityRequested.emit()
        self.win.menu_bar.duplicateLayerRequested.emit()
        self.win.menu_bar.mergeDownRequested.emit()
        self.win.menu_bar.flattenGroupRequested.emit()
        self.win.menu_bar.flattenImageRequested.emit()

    def test_06_image_and_transform_actions(self):
        """Testa acionamento das rotações e espelhamentos de Imagem."""
        self.win.menu_bar.rotate90CWRequested.emit()
        self.win.menu_bar.rotate90CCWRequested.emit()
        self.win.menu_bar.rotate180Requested.emit()
        self.win.menu_bar.flipHorizontalRequested.emit()
        self.win.menu_bar.flipVerticalRequested.emit()
        self.win.menu_bar.resetRotationRequested.emit()

    def test_07_view_and_guides_actions(self):
        """Testa acionamento das ações de Exibir (Zoom, Grade, Réguas)."""
        self.win.menu_bar.zoomInRequested.emit()
        self.win.menu_bar.zoomOutRequested.emit()
        self.win.menu_bar.resetViewRequested.emit()
        self.win.menu_bar.fitToScreenRequested.emit()
        self.win.menu_bar.toggleGridRequested.emit()
        self.win.menu_bar.toggleRulersRequested.emit()

    def test_08_dialog_instantiations(self):
        """Verifica a instanciação de todos os novos diálogos especializados."""
        from ui.core.dialogs.canvas_size_dialog import CanvasSizeDialog
        from ui.core.dialogs.modify_selection_dialog import ModifySelectionDialog
        from ui.core.dialogs.layer_properties_dialog import LayerPropertiesDialog
        from ui.core.dialogs.diagnostics_dialog import DiagnosticsDialog
        from ui.core.screens.filters.filter_adjustment_dialog import FilterAdjustmentDialog

        dlg_canvas = CanvasSizeDialog(1920, 1080, is_image_resize=False)
        self.assertEqual(dlg_canvas.get_results()["width"], 1920)

        dlg_sel = ModifySelectionDialog(mode="expand")
        self.assertEqual(dlg_sel.get_pixels(), 5)

        dlg_prop = LayerPropertiesDialog(name="Teste", opacity=0.8, blend_mode=1)
        self.assertEqual(dlg_prop.get_results()["name"], "Teste")

        dlg_diag = DiagnosticsDialog()
        self.assertIsNotNone(dlg_diag)

        dlg_filter = FilterAdjustmentDialog(initial_key="pixelate")
        self.assertIsNotNone(dlg_filter)

    def test_09_shortcuts_dialog_and_remapping(self):
        """Verifica a instanciação do diálogo de atalhos e remapeamento sem crash."""
        from ui.core.screens.keyboard_shortcuts_dialog import KeyboardShortcutsDialog

        dlg_shortcuts = KeyboardShortcutsDialog(self.win)
        self.assertIsNotNone(dlg_shortcuts)

        # Testa aplicação direta do callback no MainWindow
        test_map = {
            "tool_brush": "B",
            "tool_eraser": "E",
            "edit_undo": "Ctrl+Z",
            "edit_redo": "Ctrl+Y"
        }
        self.win._on_shortcuts_applied(test_map)
        self.assertEqual(self.win.shortcut_tool_b.key().toString(), "B")


if __name__ == "__main__":
    unittest.main()
