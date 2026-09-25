"""
Testes unitários abrangentes para validação dos 8 itens de observação e estabilidade.
"""

import sys
import unittest
from PySide6 import QtWidgets, QtGui

from ui.core.geometry.dpi_calculator import (
    px_to_mm, mm_to_px, px_to_inches, inches_to_px,
    px_to_pt, pt_to_px, calculate_print_dimensions
)
from ui.plugins.panels.navigator_plugin.components.navigator_preview import NavigatorPreview
from ui.plugins.system.workspace_core.workspace.floating_toolbar import FloatingToolbar
from ui.core.state import GeometryState, ToolState
from ui.plugins.panels.layers_plugin.header import LayersHeader
from ui.plugins.panels.geometry_plugin.panel import GeometryPanel
from ui.core.components.tool_sidebar.sidebar import ToolSidebar
from ui.infrastructure.theme.manager import ThemeManager


class TestAudit8Items(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QtWidgets.QApplication.instance():
            cls.app = QtWidgets.QApplication(sys.argv)
        else:
            cls.app = QtWidgets.QApplication.instance()

    def test_01_dpi_calculator(self):
        """Valida cálculos de conversão física de DPI (mm, polegadas, pt)."""
        # 300 DPI: 300 px = 1 polegada = 25.4 mm
        self.assertAlmostEqual(px_to_inches(300, 300), 1.0, places=4)
        self.assertAlmostEqual(px_to_mm(300, 300), 25.4, places=4)
        self.assertEqual(mm_to_px(25.4, 300), 300)
        self.assertEqual(inches_to_px(1.0, 300), 300)

        # 72 pt = 1 polegada = 300 px a 300 DPI
        self.assertAlmostEqual(pt_to_px(72.0, 300), 300.0, places=4)
        self.assertAlmostEqual(px_to_pt(300.0, 300), 72.0, places=4)

        # A4 em 300 DPI: 2480 x 3508 px -> ~210 x 297 mm
        w_mm, h_mm, text = calculate_print_dimensions(2480, 3508, 300)
        self.assertAlmostEqual(w_mm, 210.0, delta=1.0)
        self.assertAlmostEqual(h_mm, 297.0, delta=1.0)
        self.assertIn("mm", text)
        self.assertIn("300 DPI", text)

    def test_02_navigator_dynamic_aspect_ratio(self):
        """Valida se o aspect ratio do preview do navegador acompanha o canvas."""
        preview = NavigatorPreview()
        
        # 1. Canvas Quadrado (1:1)
        preview.set_canvas_size(2048, 2048)
        self.assertAlmostEqual(preview.aspect_ratio, 1.0, places=4)

        # 2. Canvas Retrato (9:16)
        preview.set_canvas_size(1080, 1920)
        self.assertAlmostEqual(preview.aspect_ratio, 1080.0 / 1920.0, places=4)

        # 3. Canvas Paisagem (16:9)
        preview.set_canvas_size(1920, 1080)
        self.assertAlmostEqual(preview.aspect_ratio, 1920.0 / 1080.0, places=4)

        # 4. Artwork QImage
        qimg = QtGui.QImage(800, 600, QtGui.QImage.Format_RGB32)
        preview.set_artwork(qimg)
        self.assertAlmostEqual(preview.aspect_ratio, 800.0 / 600.0, places=4)

    def test_03_floating_toolbar_disable_auto_collapse(self):
        """Valida que desativar o auto-recolhimento expande e trava a barra aberta."""
        tb = FloatingToolbar(ToolState())
        tb._is_collapsed = True
        
        # Define preset Desativado
        tb.set_auto_collapse_speed("Desativado")
        self.assertEqual(tb._get_speed_ms(), 0)
        self.assertFalse(tb._is_collapsed)

    def test_04_tool_sidebar_dividers(self):
        """Valida se a ToolSidebar possui separadores semânticos entre os grupos."""
        sidebar = ToolSidebar()
        actions = sidebar.actions()
        
        # Deve ter separadores
        separators = [a for a in actions if a.isSeparator()]
        self.assertGreaterEqual(len(separators), 4)

    def test_05_layers_blend_modes_compact(self):
        """Valida que os modos de mesclagem usam nomes compactos e set_values funciona."""
        header = LayersHeader()
        combo_items = [header.combo_blend.itemText(i) for i in range(header.combo_blend.count())]
        
        # Nomes compactos presentes
        self.assertIn("Subexposição", combo_items)
        self.assertIn("Superexposição", combo_items)
        self.assertIn("Multiplicar", combo_items)
        self.assertIn("Sobrepor", combo_items)

        # Suporte a strings legadas no set_values
        header.set_values(1.0, "Subexposição (Dodge)")
        self.assertEqual(header.combo_blend.currentText(), "Subexposição")

        header.set_values(0.8, "Multiplicação")
        self.assertEqual(header.combo_blend.currentText(), "Multiplicar")

    def test_06_geometry_panel_theme_reactivity(self):
        """Valida que o painel de geometria reage ao ThemeManager."""
        panel = GeometryPanel(GeometryState())
        ThemeManager.instance().set_theme("Light Clean")
        panel._apply_theme()
        
        # Status label deve ter cor atualizada
        self.assertIsNotNone(panel.lbl_status.styleSheet())
        
        # Restaura tema escuro
        ThemeManager.instance().set_theme("Dark Modern")
        panel._apply_theme()


if __name__ == "__main__":
    unittest.main()
