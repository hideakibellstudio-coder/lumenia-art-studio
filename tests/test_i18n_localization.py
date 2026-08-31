"""
Testes Unitários da Infraestrutura de Internacionalização (i18n) — Lumenia V2 (ARCcC).
========================================================================================
Valida o I18nManager, carregamento de catálogos JSON, fallback em cascata, interpolação,
emissão de sinais Qt e retranslation em tempo real da barra de menus.
"""

import os
import sys
import unittest
from PySide6 import QtWidgets, QtCore

# Garante a inicialização do QApplication para testes com QObject/QMenuBar
app = QtWidgets.QApplication.instance()
if app is None:
    app = QtWidgets.QApplication(sys.argv)

from ui.core.i18n import I18nManager, tr
from ui.core.components.menu_bar.menu_bar import MenuBar


class TestI18nLocalization(unittest.TestCase):

    def setUp(self):
        self.mgr = I18nManager.instance()
        # Salva o locale original para restaurar no tearDown
        self._orig_locale = self.mgr.get_current_locale()

    def tearDown(self):
        self.mgr.set_locale(self._orig_locale, emit_signal=False)

    def test_01_singleton_and_available_locales(self):
        """Valida se o I18nManager é singleton e expõe todos os 4 idiomas suportados."""
        mgr2 = I18nManager.instance()
        self.assertIs(self.mgr, mgr2)

        locales = self.mgr.get_available_locales()
        self.assertIn("pt_BR", locales)
        self.assertIn("en_US", locales)
        self.assertIn("es_ES", locales)
        self.assertIn("ja_JP", locales)

    def test_02_translations_across_all_locales(self):
        """Valida que uma mesma chave canônica ('menu.file.new') é traduzida corretamente nos 4 idiomas."""
        # Português
        self.mgr.set_locale("pt_BR", emit_signal=False)
        self.assertEqual(tr("menu.file.new"), "Novo Documento...")

        # Inglês
        self.mgr.set_locale("en_US", emit_signal=False)
        self.assertEqual(tr("menu.file.new"), "New Document...")

        # Espanhol
        self.mgr.set_locale("es_ES", emit_signal=False)
        self.assertEqual(tr("menu.file.new"), "Nuevo Documento...")

        # Japonês
        self.mgr.set_locale("ja_JP", emit_signal=False)
        self.assertEqual(tr("menu.file.new"), "新規ドキュメント...")

    def test_03_fallback_cascade_mechanism(self):
        """Valida o mecanismo de fallback em 4 etapas (Ativo -> en_US -> Default -> Key)."""
        self.mgr.set_locale("ja_JP", emit_signal=False)

        # Chave que não existe em nenhum idioma mas tem default fornecido
        result_default = tr("custom.untranslated.action", default="Ação Personalizada")
        self.assertEqual(result_default, "Ação Personalizada")

        # Chave que não existe e não tem default retorna a própria chave
        result_key = tr("completely.unknown.key")
        self.assertEqual(result_key, "completely.unknown.key")

    def test_04_string_interpolation(self):
        """Valida que parâmetros dinâmicos são interpolados com segurança."""
        self.mgr.set_locale("pt_BR", emit_signal=False)
        msg_pt = tr("status.doc_saved", name="Ilustracao_Final.png")
        self.assertIn("Ilustracao_Final.png", msg_pt)
        self.assertEqual(msg_pt, "Documento 'Ilustracao_Final.png' salvo com sucesso.")

        self.mgr.set_locale("en_US", emit_signal=False)
        msg_en = tr("status.doc_saved", name="Artwork_Final.png")
        self.assertEqual(msg_en, "Document 'Artwork_Final.png' saved successfully.")

    def test_05_dynamic_language_switch_signal(self):
        """Valida que set_locale emite o sinal languageChanged e persiste no QSettings."""
        received_signals = []

        def on_lang_changed(code):
            received_signals.append(code)

        self.mgr.languageChanged.connect(on_lang_changed)
        try:
            success = self.mgr.set_locale("es_ES", emit_signal=True)
            self.assertTrue(success)
            self.assertIn("es_ES", received_signals)
            self.assertEqual(self.mgr.get_current_locale(), "es_ES")

            # Verifica persistência no QSettings
            settings = QtCore.QSettings("Aladyn", "Lumenia")
            saved = settings.value("locale/current")
            self.assertEqual(saved, "es_ES")
        finally:
            self.mgr.languageChanged.disconnect(on_lang_changed)

    def test_06_menu_bar_retranslation_in_realtime(self):
        """Valida que o MenuBar reage ao sinal de troca de idioma e re-traduz seus itens dinamicamente."""
        menu_bar = MenuBar()

        # 1. Inicia em Português
        self.mgr.set_locale("pt_BR", emit_signal=True)
        self.assertEqual(menu_bar.file_menu.title(), "Arquivo")
        self.assertEqual(menu_bar.file_menu.action_new.text(), "Novo Documento...")
        self.assertEqual(menu_bar.edit_menu.title(), "Edição")
        self.assertEqual(menu_bar.help_menu.title(), "Ajuda")

        # 2. Alterna para Inglês em tempo real (zero restart)
        self.mgr.set_locale("en_US", emit_signal=True)
        self.assertEqual(menu_bar.file_menu.title(), "File")
        self.assertEqual(menu_bar.file_menu.action_new.text(), "New Document...")
        self.assertEqual(menu_bar.edit_menu.title(), "Edit")
        self.assertEqual(menu_bar.help_menu.title(), "Help")

        # 3. Alterna para Espanhol
        self.mgr.set_locale("es_ES", emit_signal=True)
        self.assertEqual(menu_bar.file_menu.title(), "Archivo")
        self.assertEqual(menu_bar.file_menu.action_new.text(), "Nuevo Documento...")
        self.assertEqual(menu_bar.edit_menu.title(), "Edición")
        self.assertEqual(menu_bar.help_menu.title(), "Ayuda")


if __name__ == "__main__":
    unittest.main()
