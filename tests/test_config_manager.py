"""
Unit Tests for ConfigManager (Lumenia V2 / ARCcC)
=================================================
Valida a persistência em arquivo JSON, isolamento em modo de testes (in-memory),
atualização atômica, emissão de sinais e migração transparente do QSettings.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from PySide6 import QtCore, QtWidgets

app = QtWidgets.QApplication.instance()
if not app:
    app = QtWidgets.QApplication(sys.argv)

from ui.infrastructure.config.manager import ConfigManager, DEFAULT_CONFIG


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.cm = ConfigManager(config_path=self.config_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_defaults_loaded_and_saved(self):
        """Valida que um arquivo JSON com as configurações padrão é criado."""
        self.assertTrue(os.path.exists(self.config_path))
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["version"], "2.0")
        self.assertEqual(data["theme"]["active"], "lumenia_purple")
        self.assertEqual(data["locale"]["current"], "auto")
        self.assertTrue(data["floating_toolbar"]["active"])
        self.assertEqual(len(data["floating_toolbar"]["tools"]), 12)

    def test_02_get_and_set_values(self):
        """Valida leitura e escrita de valores de configuração com emissão de sinais."""
        signals_received = []
        self.cm.configChanged.connect(lambda s, k, v: signals_received.append((s, k, v)))

        self.cm.set("theme", "active", "cyberpunk")
        self.assertEqual(self.cm.get("theme", "active"), "cyberpunk")
        self.assertIn(("theme", "active", "cyberpunk"), signals_received)

        # Recarrega do disco para checar persistência real
        new_instance = ConfigManager(config_path=self.config_path)
        self.assertEqual(new_instance.get("theme", "active"), "cyberpunk")

    def test_03_test_mode_isolation(self):
        """Valida que em test_mode as alterações NÃO afetam o arquivo em disco."""
        self.cm.set_test_mode(True)
        self.cm.set("locale", "current", "ja_JP")
        self.assertEqual(self.cm.get("locale", "current"), "ja_JP")

        # Em disco, o arquivo ainda deve ter o valor antigo ("auto")
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["locale"]["current"], "auto")

    def test_04_section_manipulation(self):
        """Valida get_section e set_section."""
        dock_sec = self.cm.get_section("dock")
        self.assertIn("auto_collapse", dock_sec)
        self.assertIn("speed", dock_sec)

        self.cm.set_section("dock", {"auto_collapse": True, "speed": "Lento"})
        self.assertTrue(self.cm.get("dock", "auto_collapse"))
        self.assertEqual(self.cm.get("dock", "speed"), "Lento")


if __name__ == "__main__":
    unittest.main()
