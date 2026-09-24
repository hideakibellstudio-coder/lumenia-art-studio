"""
Test suite for the 5 User Observations Audit and Verification in Lumenia V2.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6 import QtCore, QtGui, QtWidgets

# Assegura que QApplication existe
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from ui.core.icons import get_icon, SVG_ICONS
from ui.core.engine.registry import EngineRegistry
from ui.engine_backends.aladyn import AladynBackend
from ui.core.screens.keyboard_shortcuts_dialog import KeyboardShortcutsDialog, DEFAULT_SHORTCUTS
from ui.core.screens.cursor_settings_dialog import CursorSettingsDialog
from plugins.system.workspace_core.workspace.canvas.renderers.tool_cursor_renderer import ToolCursorRenderer
from ui.core.dialogs.render_settings_dialog import RenderSettingsDialog, load_render_settings, save_render_settings


class Test5ObservationsAudit(unittest.TestCase):

    def setUp(self):
        self.backend = AladynBackend()

    # ── Item 1: Undo/Redo Dynamic Limit ──────────────────────────────────────
    def test_undo_limit_cpp_and_backend(self):
        # Testa getters e setters dinâmicos de memória e passos
        self.backend.set_undo_memory_limit_mb(512)
        self.assertEqual(self.backend.get_undo_memory_limit_mb(), 512)

        self.backend.set_undo_max_steps(100)
        self.assertEqual(self.backend.get_undo_max_steps(), 100)

        # Testa persistência de configurações de renderização
        cfg = {"undo_limit_mb": 1024, "undo_max_steps": 200, "low_latency": True, "linear_gamma": False, "deep_color": True, "profile_id": 0}
        save_render_settings(cfg)
        loaded = load_render_settings()
        self.assertEqual(loaded.get("undo_limit_mb"), 1024)
        self.assertEqual(loaded.get("undo_max_steps"), 200)

    # ── Item 2: Keyboard Shortcuts Dialog ────────────────────────────────────
    def test_keyboard_shortcuts_dialog(self):
        dlg: KeyboardShortcutsDialog = KeyboardShortcutsDialog()
        # dlg.card não existe mais: migrado para BaseFramelessDialog em 2026-09-18
        # (panorama-consistencia-visual-tema, Achado #4) -- root_container é o
        # equivalente herdado da base compartilhada por ~20 outros diálogos.
        self.assertIsNotNone(dlg.root_container)
        self.assertGreater(dlg.table.rowCount(), 0)

        # Testa filtragem por categoria
        dlg._on_category_changed(1) # Ferramentas
        self.assertGreater(dlg.table.rowCount(), 0)

        # Testa busca em tempo real
        dlg._on_category_changed(0) # Todas
        dlg._on_search_changed("Pincel")
        self.assertEqual(dlg.table.rowCount(), 1)

        # Testa gravação de atalho
        dlg._on_shortcut_recorded("tool_brush", "Ctrl+Alt+B")
        self.assertEqual(dlg._shortcuts_map["tool_brush"], "Ctrl+Alt+B")

    # ── Item 3: Icons Consistency ────────────────────────────────────────────
    def test_icons_and_clean_layer_consistency(self):
        # Checa presença de ícones solicitados
        self.assertIn("clean_layer", SVG_ICONS)
        self.assertIn("chevron_up", SVG_ICONS)
        self.assertIn("chevron_down", SVG_ICONS)
        self.assertIn("keyboard", SVG_ICONS)
        self.assertIn("cursor", SVG_ICONS)

        # Garante que get_icon retorna QIcon válido (não nulo) inclusive com aliases
        self.assertFalse(get_icon("clean_layer").isNull())
        self.assertFalse(get_icon("clean-layer").isNull())
        self.assertFalse(get_icon("chevron_up").isNull())
        self.assertFalse(get_icon("chevron-up").isNull())
        self.assertFalse(get_icon("chevron_down").isNull())
        self.assertFalse(get_icon("chevron-down").isNull())

    # ── Item 4: Tool Cursor & Settings Dialog ────────────────────────────────
    def test_cursor_renderer_and_dialog(self):
        # Testa renderização de anel e crosshair sem erros
        img = QtGui.QImage(200, 200, QtGui.QImage.Format_ARGB32)
        p = QtGui.QPainter(img)
        ToolCursorRenderer.render_cursor(p, 100, 100, 24.0, 1.0, False, {"mode": "ring_and_dot", "ring_opacity": 0.9})
        ToolCursorRenderer.render_cursor(p, 100, 100, 24.0, 1.0, False, {"mode": "crosshair", "ring_opacity": 0.9})
        p.end()

        # Testa criação de cursores SVG personalizados
        cur_wand = ToolCursorRenderer.create_custom_cursor("wand")
        self.assertIsNotNone(cur_wand)
        cur_drop = ToolCursorRenderer.create_custom_cursor("eyedropper")
        self.assertIsNotNone(cur_drop)

        # Testa Diálogo de Configurações de Cursor
        dlg: CursorSettingsDialog = CursorSettingsDialog()
        # dlg.card não existe mais: migrado para BaseFramelessDialog em 2026-09-18
        # (panorama-consistencia-visual-tema, Achado #4) -- root_container é o
        # equivalente herdado da base compartilhada por ~20 outros diálogos.
        self.assertIsNotNone(dlg.root_container)
        self.assertIsNotNone(dlg.btn_group)

        # Testa cálculo de bounding rect do cursor
        rect = ToolCursorRenderer.get_cursor_rect(100.0, 100.0, 30.0, 1.5, margin=10)
        self.assertEqual(rect.center().x(), 100)
        self.assertEqual(rect.center().y(), 100)
        self.assertGreater(rect.width(), 60)

        # Testa DocumentManager has_document helper
        from ui.core.document.manager import DocumentManager
        dm = DocumentManager.instance()
        self.assertIsInstance(dm.has_document(), bool)

    # ── Item 5: Navigator Dynamic Dimensions Pan Sync ────────────────────────
    def test_navigator_pan_dynamic_sync(self):
        from plugins.system.workspace_core.workspace.workspace_document_sync import WorkspaceDocSyncMixin

        class MockCanvas:
            canvas_w = 2480 # Ex: A4 alta resolução
            canvas_h = 3508
            zoom = 1.0
            pan_x = 0.0
            pan_y = 0.0
            rotation = 0.0
            published = None
            def publish_view(self, zoom_changed=False, notify_camera=True):
                self.published = (zoom_changed, notify_camera)

        class MockSync(QtCore.QObject, WorkspaceDocSyncMixin):
            zoomChanged = QtCore.Signal(float)

            def __init__(self):
                super().__init__()
                self.canvas_widget = MockCanvas()
                self.canvas_w = 1920 # Default antigo
                self.canvas_h = 1080
                self._properties_dock = None

        sync = MockSync()
        # Aplica quina exata (norm_x=1.0, norm_y=1.0)
        sync._set_camera_from_navigator(1.0, 1.0, 1.0, 0.0)
        # Verifica se usou a largura real 2480x3508 e não o padrão estático 1920x1080
        expected_pan_x = (0.5 - 1.0) * 1.0 * 2480 # -1240.0
        expected_pan_y = (0.5 - 1.0) * 1.0 * 3508 # -1754.0
        self.assertEqual(sync.canvas_widget.pan_x, expected_pan_x)
        self.assertEqual(sync.canvas_widget.pan_y, expected_pan_y)
        # Veio do Navigator: publica o zoom mas não devolve cameraChanged a ele.
        self.assertEqual(sync.canvas_widget.published, (True, False))


if __name__ == "__main__":
    unittest.main()
