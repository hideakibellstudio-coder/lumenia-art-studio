import os
import sys
import json
import re
import unittest
from PySide6 import QtWidgets

app = QtWidgets.QApplication.instance()
if not app:
    app = QtWidgets.QApplication(sys.argv)

from ui.infrastructure.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.widgets.slider.step_button import SliderStepButton


class TestThemeSystem(unittest.TestCase):
    def setUp(self):
        self.tm = ThemeManager.instance()

    def test_01_all_theme_files_valid_and_complete(self):
        themes_dir = os.path.join(os.path.dirname(__file__), '..', 'ui', 'infrastructure', 'theme', 'themes')
        theme_files = [f for f in os.listdir(themes_dir) if f.endswith('.json')]
        self.assertGreaterEqual(len(theme_files), 9)

        expected_tokens = {
            'BG_DARKEST', 'BG_DARKER', 'BG_DARK', 'BG_MID', 'BG_TERTIARY',
            'BG_LIGHT', 'BG_LIGHTER', 'BG_LIGHTEST',
            'FG_PRIMARY', 'FG_SECONDARY', 'FG_TERTIARY', 'FG_LINK',
            'ACCENT', 'ACCENT_HOVER', 'ACCENT_MUTED',
            'DANGER', 'DANGER_HOVER', 'SUCCESS', 'WARNING',
            'BORDER', 'BORDER_LIGHT', 'SHADOW', 'TRANSPARENT'
        }

        for tf in theme_files:
            path = os.path.join(themes_dir, tf)
            with open(path, 'r', encoding='utf-8') as f_in:
                data = json.load(f_in)

            self.assertIn('metadata', data, f'{tf} sem metadata')
            self.assertIn('colors', data, f'{tf} sem colors')
            colors = data['colors']

            missing = expected_tokens - set(colors.keys())
            self.assertEqual(len(missing), 0, f'{tf} está faltando tokens: {missing}')

    def test_02_qss_compilation_no_unresolved_tokens(self):
        themes_dir = os.path.join(os.path.dirname(__file__), '..', 'ui', 'infrastructure', 'theme', 'themes')
        theme_keys = [f[:-5] for f in os.listdir(themes_dir) if f.endswith('.json')]

        for key in theme_keys:
            self.tm._current_theme = key
            qss = self.tm.get_stylesheet()
            self.assertIsNotNone(qss, f'Falha ao compilar tema {key}')
            self.assertGreater(len(qss), 500, f'QSS compilado muito curto para {key}')

            unresolved = re.findall(r'@[A-Z_]+', qss)
            self.assertEqual(unresolved, [], f'Tokens não resolvidos no QSS do tema {key}: {unresolved}')

        # Restaura tema padrão
        self.tm._current_theme = 'lumenia_purple'

    def test_03_color_and_alias_resolution(self):
        self.tm.apply_theme('lumenia_purple')
        self.assertTrue(self.tm.get_color('bg_main').startswith('#'))
        self.assertTrue(self.tm.get_color('bg_canvas').startswith('#'))
        self.assertTrue(self.tm.get_color('bg_panel').startswith('#'))
        self.assertTrue(self.tm.get_color('border').startswith('#'))
        self.assertTrue(self.tm.get_color('accent').startswith('#'))
        self.assertTrue(self.tm.get_color('text_main').startswith('#'))
        self.assertTrue(self.tm.get_color('text_sec').startswith('#'))
        self.assertTrue(self.tm.get_color('danger').startswith('#'))
        self.assertTrue(self.tm.get_color('success').startswith('#'))

    def test_04_theme_switching_signal(self):
        received_themes = []
        self.tm.themeChanged.connect(lambda t: received_themes.append(t))

        self.tm.apply_theme('light_default')
        self.assertIn('light_default', received_themes)
        self.assertFalse(self.tm.is_dark)

        self.tm.apply_theme('cyberpunk')
        self.assertIn('cyberpunk', received_themes)
        self.assertTrue(self.tm.is_dark)

        self.tm.apply_theme('lumenia_purple')

    def test_05_widget_theme_reactivity(self):
        dlg = BaseFramelessDialog('Teste de Diálogo')
        _step_btn = SliderStepButton(is_plus=True, style_type='round')  # vivo durante a troca de tema

        self.tm.apply_theme('light_default')
        self.tm.apply_theme('dark_default')
        self.tm.apply_theme('lumenia_purple')

        self.assertIsNotNone(dlg.root_container.styleSheet())
        dlg.close()

    def test_06_ui_scale_getter_setter_and_persistence(self):
        from ui.infrastructure.config.manager import ConfigManager
        cfg = ConfigManager.instance()

        orig_scale = self.tm.ui_scale
        scale_events = []
        self.tm.scaleChanged.connect(scale_events.append)

        try:
            self.tm.set_ui_scale(0.8)
            self.assertAlmostEqual(self.tm.ui_scale, 0.8)
            self.assertIn(0.8, scale_events)
            self.assertAlmostEqual(cfg.get("interface", "scale", 1.0), 0.8)

            qss_80 = self.tm._compile_qss("QPushButton { font-size: 10px; min-height: 20px; }")
            self.assertIn("8px", qss_80)
            self.assertIn("16px", qss_80)

            self.tm.set_ui_scale(1.5)
            self.assertAlmostEqual(self.tm.ui_scale, 1.5)
            self.assertIn(1.5, scale_events)
            self.assertAlmostEqual(cfg.get("interface", "scale", 1.0), 1.5)

            qss_150 = self.tm._compile_qss("QPushButton { font-size: 10px; min-height: 20px; }")
            self.assertIn("15px", qss_150)
            self.assertIn("30px", qss_150)
        finally:
            self.tm.set_ui_scale(orig_scale)

    def test_07_bars_scale_reactivity(self):
        from ui.core.components.tool_sidebar.sidebar import ToolSidebar
        from ui.plugins.system.workspace_core.workspace.floating_toolbar import FloatingToolbar
        from ui.core.state import ToolState

        orig_scale = self.tm.ui_scale
        try:
            self.tm.set_ui_scale(1.0)
            sidebar = ToolSidebar()
            float_bar = FloatingToolbar(ToolState())

            self.assertEqual(sidebar.iconSize().width(), 20)
            btn = next(iter(float_bar.buttons.values()))
            self.assertEqual(btn.width(), 38)
            self.assertEqual(btn.iconSize().width(), 22)

            self.tm.set_ui_scale(0.8)
            self.assertEqual(sidebar.iconSize().width(), 16)
            self.assertEqual(btn.width(), int(38 * 0.8))
            self.assertEqual(btn.iconSize().width(), int(22 * 0.8))

            self.tm.set_ui_scale(1.5)
            self.assertEqual(sidebar.iconSize().width(), 30)
            self.assertEqual(btn.width(), int(38 * 1.5))
            self.assertEqual(btn.iconSize().width(), int(22 * 1.5))

            sidebar.deleteLater()
            float_bar.deleteLater()
        finally:
            self.tm.set_ui_scale(orig_scale)


if __name__ == '__main__':
    unittest.main()
