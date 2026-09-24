"""Test Menu Bar Complete Wiring & Dialogs — Validação de Todas as Ações do Menu."""

import unittest
import sys
import os

from PySide6 import QtCore, QtGui, QtWidgets
from ui.boundary.orchestrator.main_window import MainWindow
from ui.core.components.menu_bar.menu_bar import MenuBar

# Assegura que QApplication existe em modo offscreen
app = QtWidgets.QApplication.instance()
if app is None:
    app = QtWidgets.QApplication(["--platform", "offscreen"])


class TestMenuBarCompleteWiring(unittest.TestCase):
    """Suíte de testes de integração para todos os menus e ações do MenuBar."""

    @classmethod
    def setUpClass(cls):
        from tests.main_window_fixture import main_window_com_workspace
        cls.win = main_window_com_workspace()

    def setUp(self):
        pass

    def test_01_menu_bar_submenus_exist(self):
        """Verifica se todos os 10 submenus estão instanciados no menu_bar."""
        mb: MenuBar = self.win.menu_bar
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
        # NOTA: a ação "Limpar" (antigo clearCanvasRequested) foi removida do
        # menu Arquivo -- Editar > Limpar Conteúdo da Camada (clearLayerRequested)
        # é o único ponto de acesso agora. Ver
        # claude/panorama-menu-bar-fluxo-navigator.md.
        self.win.menu_bar.saveDocumentRequested.emit()

    def test_03_edit_and_clipboard_actions(self):
        """Testa acionamento das ações de Edição e Área de Transferência."""
        self.win.menu_bar.undoRequested.emit()
        self.win.menu_bar.redoRequested.emit()
        self.win.menu_bar.copyRequested.emit()
        self.win.menu_bar.cutRequested.emit()
        self.win.menu_bar.fillRequested.emit()

    def test_03b_undo_redo_history_state_feedback(self):
        """Verifica a sincronização reativa de disponibilidade visual em Undo/Redo."""
        mb = self.win.menu_bar
        edit_menu = mb.edit_menu
        self.assertIsNotNone(edit_menu)

        mb.update_history_state(False, False)
        self.assertFalse(edit_menu.act_undo.isEnabled())
        self.assertFalse(edit_menu.act_redo.isEnabled())

        mb.update_history_state(True, False)
        self.assertTrue(edit_menu.act_undo.isEnabled())
        self.assertFalse(edit_menu.act_redo.isEnabled())

        mb.update_history_state(False, True)
        self.assertFalse(edit_menu.act_undo.isEnabled())
        self.assertTrue(edit_menu.act_redo.isEnabled())

        mb.update_history_state(True, True)
        self.assertTrue(edit_menu.act_undo.isEnabled())
        self.assertTrue(edit_menu.act_redo.isEnabled())

        if hasattr(self.win, "tool_sidebar") and self.win.tool_sidebar:
            sidebar = self.win.tool_sidebar
            sidebar.update_history_state(False, False)
            self.assertFalse(sidebar.action_undo.isEnabled())
            self.assertFalse(sidebar.action_redo.isEnabled())

            sidebar.update_history_state(True, True)
            self.assertTrue(sidebar.action_undo.isEnabled())
            self.assertTrue(sidebar.action_redo.isEnabled())

        self.win.update_undo_redo_actions()

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

    def test_07b_soft_proof_toggle(self):
        """Verifica o toggle leve de Prova de Cores (Exibir), sem RenderSettingsDialog."""
        action = self.win.menu_bar.view_menu.action_proof
        self.assertTrue(action.isCheckable())

        # Liga via UI (dispara toggled -> toggleSoftProofRequested -> toggle_soft_proof)
        action.setChecked(True)
        self.assertTrue(self.win.menu_bar.view_menu.action_proof.isChecked())

        action.setChecked(False)
        self.assertFalse(self.win.menu_bar.view_menu.action_proof.isChecked())

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

        # Testa aplicação direta do callback (DialogActions.apply_shortcuts)
        test_map = {
            "tool_brush": "B",
            "tool_eraser": "E",
            "edit_undo": "Ctrl+Z",
            "edit_redo": "Ctrl+Y"
        }
        self.win.dialogs.apply_shortcuts(test_map)
        self.assertEqual(self.win.shortcut_registry.targets["tool_brush"].key().toString(), "B")

    def test_10_telemetry_grid_window_and_shortcut(self):
        """Verifica a abertura e funcionamento do Cockpit de Telemetria em Grid (F12)."""
        from ui.core.dialogs.telemetry_grid_window import TelemetryGridWindow

        # 1. Instanciação direta
        grid_win = TelemetryGridWindow(self.win)
        self.assertIsNotNone(grid_win)
        self.assertEqual(len(grid_win._cards), 20)
        self.assertTrue(grid_win._stay_on_top)

        # 2. Toggle Stay-on-Top
        grid_win._on_toggle_pin()
        self.assertFalse(grid_win._stay_on_top)
        grid_win._on_toggle_pin()
        self.assertTrue(grid_win._stay_on_top)

        # 3. Refresh de métricas sem crash
        grid_win._refresh_metrics()

        # 4. Acionamento via sinal do menu_bar
        self.win.menu_bar.telemetryGridRequested.emit()
        telemetry = self.win.dialogs.telemetry_window
        self.assertIsNotNone(telemetry)
        self.assertTrue(telemetry.isVisible())

        # Limpeza
        grid_win.deleteLater()
        telemetry.close()


if __name__ == "__main__":
    unittest.main()
