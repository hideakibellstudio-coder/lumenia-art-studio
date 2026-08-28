"""Unit tests for NewDocumentDialog, PresetCatalog and memory estimation."""

import os
import unittest
from PySide6 import QtWidgets, QtCore

from ui.core.screens.new_document.preset_catalog import (
    PRESET_CATEGORIES,
    BACKGROUND_COLORS,
    PAPER_TEXTURES,
    COLOR_PROFILES,
    estimate_ram_usage_mb,
)
from ui.core.screens.new_document_dialog import NewDocumentDialog


class TestNewDocumentDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance()
        if cls.app is None:
            cls.app = QtWidgets.QApplication([])

    def test_preset_catalog_integrity(self):
        """Verifica se todas as categorias e presets do catálogo estão íntegros e consistentes."""
        self.assertIn("illustration", PRESET_CATEGORIES)
        self.assertIn("web_screen", PRESET_CATEGORIES)
        self.assertIn("social_media", PRESET_CATEGORIES)
        self.assertIn("cinema", PRESET_CATEGORIES)

        for cat_key, cat_data in PRESET_CATEGORIES.items():
            self.assertIn("name", cat_data)
            self.assertIn("presets", cat_data)
            self.assertGreater(len(cat_data["presets"]), 0)
            for p in cat_data["presets"]:
                pid, name, w, h, dpi, icon_name, desc = p
                self.assertGreater(w, 0)
                self.assertGreater(h, 0)
                self.assertGreater(dpi, 0)

    def test_ram_estimation_formula(self):
        """Valida o cálculo de consumo de memória RAM do canvas."""
        # 1920x1080 com 3 camadas
        # 1920 * 1080 * 4 = 8.294.400 bytes por camada
        # 8.294.400 * 4.5 = 37.324.800 bytes = ~35.59 MB
        mb = estimate_ram_usage_mb(1920, 1080, num_layers=3)
        self.assertAlmostEqual(mb, 35.5957, places=2)

        # 4K (3840x2160) com 3 camadas = 4x Full HD = ~142.38 MB
        mb_4k = estimate_ram_usage_mb(3840, 2160, num_layers=3)
        self.assertAlmostEqual(mb_4k, 35.5957 * 4, places=1)

    def test_dialog_initialization_and_params(self):
        """Valida a instanciação da janela e os parâmetros padrão retornados."""
        dlg = NewDocumentDialog()
        params = dlg.get_document_params()

        self.assertIn("name", params)
        self.assertIn("width", params)
        self.assertIn("height", params)
        self.assertIn("dpi", params)
        self.assertIn("color_profile_id", params)
        self.assertIn("bg_color", params)
        self.assertIn("paper_texture_id", params)

        # Padrão inicial: A4 Ilustração (2480x3508, 300 DPI)
        self.assertEqual(params["width"], 2480)
        self.assertEqual(params["height"], 3508)
        self.assertEqual(params["dpi"], 300)

    def test_dialog_swap_orientation(self):
        """Valida a inversão de orientação rápida (Paisagem <-> Retrato)."""
        dlg = NewDocumentDialog()
        w_orig = dlg.spn_width.value()
        h_orig = dlg.spn_height.value()

        # Clica no botão swap
        dlg._on_swap_orientation()
        self.assertEqual(dlg.spn_width.value(), h_orig)
        self.assertEqual(dlg.spn_height.value(), w_orig)

        # Clica novamente para voltar
        dlg._on_swap_orientation()
        self.assertEqual(dlg.spn_width.value(), w_orig)
        self.assertEqual(dlg.spn_height.value(), h_orig)

    def test_dialog_category_and_card_selection(self):
        """Valida a navegação entre categorias de abas e seleção de cards."""
        dlg = NewDocumentDialog()
        
        # Alterna para categoria Web (índice 1)
        dlg.tab_categories.setCurrentIndex(1)
        self.assertEqual(dlg._selected_category, "web_screen")
        self.assertGreater(len(dlg._preset_cards), 0)

        # Clica no card 4K UHD
        card_4k = dlg._preset_cards[0]
        card_4k.clicked.emit(card_4k.preset_id, card_4k.p_width, card_4k.p_height, card_4k.p_dpi)

        params = dlg.get_document_params()
        self.assertEqual(params["width"], 3840)
        self.assertEqual(params["height"], 2160)
        self.assertEqual(params["dpi"], 72)


if __name__ == "__main__":
    unittest.main()
