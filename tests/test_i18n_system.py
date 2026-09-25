"""
Unit Tests for I18nManager & Internationalization System (Lumenia V2 / ARCcC)
=============================================================================
Valida a detecção automática do idioma do SO, fallback universal para en_US,
interpolação dinâmica de parâmetros e hot-swap em tempo real sem restart.
"""

import os
import sys
import unittest
from PySide6 import QtCore, QtWidgets

app = QtWidgets.QApplication.instance()
if not app:
    app = QtWidgets.QApplication(sys.argv)

from ui.infrastructure.i18n import I18nManager, tr


class TestI18nSystem(unittest.TestCase):
    def setUp(self):
        from ui.infrastructure.config import ConfigManager
        ConfigManager.instance().set_test_mode(True)
        self.mgr = I18nManager.instance()
        self._orig_locale = self.mgr.get_current_locale()

    def tearDown(self):
        self.mgr.set_locale(self._orig_locale, emit_signal=False)
        from ui.infrastructure.config import ConfigManager
        ConfigManager.instance().set_test_mode(False)

    def test_01_system_locale_detection_and_fallback(self):
        """Valida que detect_system_locale() retorna um código suportado ou en_US como fallback."""
        detected = self.mgr.detect_system_locale()
        self.assertIn(detected, self.mgr.SUPPORTED_LOCALES)

    def test_02_canonical_translations_and_fallbacks(self):
        """Valida que chaves são traduzidas corretamente em pt_BR e en_US com fallback."""
        self.mgr.set_locale("en_US", is_auto=False)
        self.assertEqual(tr("menu.file.title"), "File")
        self.assertEqual(tr("tools.brush"), "Brush (B)")

        self.mgr.set_locale("pt_BR", is_auto=False)
        self.assertEqual(tr("menu.file.title"), "Arquivo")
        self.assertEqual(tr("tools.brush"), "Pincel (B)")

        # Chave inexistente deve cair no fallback default
        self.assertEqual(tr("non.existent.key", "Texto Padrão"), "Texto Padrão")

    def test_03_parameter_interpolation(self):
        """Valida que variáveis com {name} são interpoladas corretamente."""
        self.mgr.set_locale("pt_BR", is_auto=False)
        msg_pt = tr("status.doc_saved", name="Ilustracao.png")
        self.assertIn("Ilustracao.png", msg_pt)

        self.mgr.set_locale("en_US", is_auto=False)
        msg_en = tr("status.doc_saved", name="Artwork.png")
        self.assertIn("Artwork.png", msg_en)

    def test_05_brush_presets_and_tool_options_across_languages(self):
        """Valida que receitas de pincel, seções avançadas e opções de ferramentas traduzem nos 4 idiomas."""
        from ui.plugins.panels.brush_plugin.presets_data import get_preset_display_name, get_category_display_name
        from ui.core.tools import get_tool_name

        # 1. Português
        self.mgr.set_locale("pt_BR", is_auto=False)
        self.assertEqual(get_preset_display_name("Pincel Redondo"), "Pincel Redondo")
        self.assertEqual(get_preset_display_name("G-Pen (Mangá)"), "G-Pen (Mangá)")
        self.assertEqual(get_category_display_name("pencil"), "Lápis & Carvão")
        self.assertEqual(get_tool_name("eyedrop"), "Conta-Gotas (I)")
        self.assertEqual(tr("brush.sec_size_opacity"), "1. Tamanho, Opacidade & Mesclagem")
        self.assertEqual(tr("engine_params.pencil_hard"), "Dureza do Grafite (2H-6B)")

        # 2. Inglês
        self.mgr.set_locale("en_US", is_auto=False)
        self.assertEqual(get_preset_display_name("Pincel Redondo"), "Round Brush")
        self.assertEqual(get_preset_display_name("G-Pen (Mangá)"), "G-Pen (Manga)")
        self.assertEqual(get_category_display_name("pencil"), "Pencils & Charcoal")
        self.assertEqual(get_tool_name("eyedrop"), "Eyedropper (I)")
        self.assertEqual(tr("brush.sec_size_opacity"), "1. Size, Opacity & Blending")
        self.assertEqual(tr("engine_params.pencil_hard"), "Graphite Hardness (2H-6B)")

        # 3. Espanhol
        self.mgr.set_locale("es_ES", is_auto=False)
        self.assertEqual(get_preset_display_name("Pincel Redondo"), "Pincel Redondo")
        self.assertEqual(get_preset_display_name("G-Pen (Mangá)"), "Pluma G (Manga)")
        self.assertEqual(get_category_display_name("pencil"), "Lápices y Carboncillo")
        self.assertEqual(get_tool_name("eyedrop"), "Cuentagotas (I)")
        self.assertEqual(tr("brush.sec_size_opacity"), "1. Tamaño, Opacidad y Fusión")
        self.assertEqual(tr("engine_params.pencil_hard"), "Dureza del Grafito (2H-6B)")

        # 4. Japonês
        self.mgr.set_locale("ja_JP", is_auto=False)
        self.assertEqual(get_preset_display_name("Pincel Redondo"), "丸ブラシ")
        self.assertEqual(get_preset_display_name("G-Pen (Mangá)"), "Gペン (マンガ)")
        self.assertEqual(get_category_display_name("pencil"), "鉛筆・木炭")
        self.assertEqual(get_tool_name("eyedrop"), "スポイト (I)")
        self.assertEqual(tr("brush.sec_size_opacity"), "1. サイズ・不透明度・合成")
        self.assertEqual(tr("engine_params.pencil_hard"), "芯の硬度 (2H-6B)")


if __name__ == "__main__":
    unittest.main()
