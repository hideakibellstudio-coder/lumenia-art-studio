"""
Test Suite: Dialogs Theme Reactivity, i18n & Documentation
==========================================================
Valida a reatividade dinâmica de tema e internacionalização completa (pt_BR, en_US, es_ES, ja_JP)
nos 5 diálogos principais do Lumenia, além dos novos diálogos UserGuideDialog e TestReportDialog.
"""

import os
import unittest
from PySide6 import QtWidgets, QtCore
from ui.core.theme.manager import ThemeManager
from ui.core.i18n import I18nManager, tr
from ui.core.screens.plugins.dialog import PluginsWindow
from ui.core.dialogs.render_settings_dialog import RenderSettingsDialog
from ui.core.screens.keyboard_shortcuts_dialog import KeyboardShortcutsDialog
from ui.core.screens.filters.filter_adjustment_dialog import FilterAdjustmentDialog
from ui.core.screens.about_dialog import AboutDialog
from ui.core.dialogs.user_guide_dialog import UserGuideDialog
from ui.core.dialogs.test_report_dialog import TestReportDialog
from ui.core.components.menu_bar.help_menu import HelpMenu


class TestDialogsThemeAndDocs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance()
        if not cls.app:
            cls.app = QtWidgets.QApplication([])

    def setUp(self):
        self.tm = ThemeManager.instance()
        self.i18n = I18nManager.instance()
        self.i18n.set_locale("pt_BR", is_auto=False, emit_signal=False)

    def test_01_plugins_window_theme_and_i18n(self):
        """Valida que PluginsWindow não trava com troca de tema e suporta os 4 idiomas."""
        dialog = PluginsWindow()
        self.assertIsNotNone(dialog)

        # Troca de temas (sem lançar exceções)
        for theme_name in ["dark_default", "light_default", "lumenia_purple"]:
            self.tm.apply_theme(theme_name)
            self.app.processEvents()

        # Troca de idiomas
        for loc in ["pt_BR", "en_US", "es_ES", "ja_JP"]:
            self.i18n.set_locale(loc, is_auto=False, emit_signal=True)
            self.app.processEvents()

        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

    def test_02_render_settings_dialog_theme_and_i18n(self):
        """Valida que RenderSettingsDialog e ProfileCard recebem themeChanged sem TypeError."""
        dialog = RenderSettingsDialog()
        self.assertIsNotNone(dialog)

        for theme_name in ["dark_default", "light_default", "lumenia_purple"]:
            self.tm.apply_theme(theme_name)
            self.app.processEvents()

        for loc in ["pt_BR", "en_US", "es_ES", "ja_JP"]:
            self.i18n.set_locale(loc, is_auto=False, emit_signal=True)
            self.app.processEvents()

        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

    def test_03_keyboard_shortcuts_dialog_theme_and_i18n(self):
        """Valida KeyboardShortcutsDialog herdando de BaseFramelessDialog com tema e i18n."""
        dialog = KeyboardShortcutsDialog()
        self.assertIsNotNone(dialog)

        for theme_name in ["dark_default", "light_default", "lumenia_purple"]:
            self.tm.apply_theme(theme_name)
            self.app.processEvents()

        for loc in ["pt_BR", "en_US", "es_ES", "ja_JP"]:
            self.i18n.set_locale(loc, is_auto=False, emit_signal=True)
            self.app.processEvents()

        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

    def test_04_filter_adjustment_dialog_theme_and_i18n(self):
        """Valida FilterAdjustmentDialog e FilterCard com tema e i18n dinâmicos."""
        dialog = FilterAdjustmentDialog()
        self.assertIsNotNone(dialog)

        for theme_name in ["dark_default", "light_default", "lumenia_purple"]:
            self.tm.apply_theme(theme_name)
            self.app.processEvents()

        for loc in ["pt_BR", "en_US", "es_ES", "ja_JP"]:
            self.i18n.set_locale(loc, is_auto=False, emit_signal=True)
            self.app.processEvents()

        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

    def test_05_about_dialog_theme_and_i18n(self):
        """Valida AboutDialog com estilização explícita de especificações do motor."""
        dialog = AboutDialog()
        self.assertIsNotNone(dialog)

        for theme_name in ["dark_default", "light_default", "lumenia_purple"]:
            self.tm.apply_theme(theme_name)
            self.app.processEvents()

        for loc in ["pt_BR", "en_US", "es_ES", "ja_JP"]:
            self.i18n.set_locale(loc, is_auto=False, emit_signal=True)
            self.app.processEvents()

        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

    def test_06_user_guide_dialog_markdown_and_languages(self):
        """Valida UserGuideDialog carregando os 4 markdowns e alternando idioma."""
        dialog = UserGuideDialog()
        self.assertIsNotNone(dialog)

        # Testa carregamento em cada um dos idiomas
        for loc in ["pt_BR", "en_US", "es_ES", "ja_JP"]:
            self.i18n.set_locale(loc, is_auto=False, emit_signal=True)
            self.app.processEvents()
            md_text = dialog.browser.toPlainText()
            self.assertTrue(len(md_text) > 50, f"Markdown de {loc} vazio ou não carregado!")

        for theme_name in ["dark_default", "light_default"]:
            self.tm.apply_theme(theme_name)
            self.app.processEvents()

        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

    def test_07_test_report_dialog_metrics_and_languages(self):
        """Valida TestReportDialog renderizando KPIs, tabela de módulos e i18n."""
        dialog = TestReportDialog()
        self.assertIsNotNone(dialog)

        self.assertEqual(dialog.table.rowCount(), 8)
        self.assertEqual(len(dialog.kpi_cards), 4)

        for loc in ["pt_BR", "en_US", "es_ES", "ja_JP"]:
            self.i18n.set_locale(loc, is_auto=False, emit_signal=True)
            self.app.processEvents()

        for theme_name in ["dark_default", "light_default"]:
            self.tm.apply_theme(theme_name)
            self.app.processEvents()

        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

    def test_08_help_menu_wiring(self):
        """Valida ações e sinais em HelpMenu."""
        menu = HelpMenu()
        self.assertIsNotNone(menu.act_guide)
        self.assertIsNotNone(menu.act_test_report)
        self.assertIsNotNone(menu.act_shortcuts)
        self.assertIsNotNone(menu.act_diag)
        self.assertIsNotNone(menu.act_about)

        # Testa re-tradução do HelpMenu
        for loc in ["pt_BR", "en_US", "es_ES", "ja_JP"]:
            self.i18n.set_locale(loc, is_auto=False, emit_signal=True)
            self.app.processEvents()

        menu.deleteLater()
        self.app.processEvents()

    def test_09_feedback_html_multilingual(self):
        """Valida que Enviar_Feedback.html contém suporte a múltiplos idiomas e carrega locale ativo."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        feedback_path = os.path.join(project_root, "Enviar_Feedback.html")
        self.assertTrue(os.path.exists(feedback_path), "Enviar_Feedback.html não encontrado na raiz!")

        with open(feedback_path, "r", encoding="utf-8") as f:
            content = f.read()

        for lang in ["pt_BR", "en_US", "es_ES", "ja_JP"]:
            self.assertTrue(f'{lang}:' in content or f'"{lang}":' in content, f"Configuração de idioma {lang} ausente no Enviar_Feedback.html!")

        self.assertIn("changeLanguage", content)
        self.assertIn("generateComprehensiveReport", content)
        self.assertIn("langSelector", content)


if __name__ == "__main__":
    unittest.main()
