#!/usr/bin/env python3
"""
Test Suite: Dialogs & Configuration I18n Retranslation
Valida se todos os diálogos de preferências e as opções de ferramentas da barra secundária
acompanham a mudança de idioma em tempo real (pt_BR, en_US, es_ES, ja_JP).
"""

import os
import sys
import unittest
from PySide6 import QtCore, QtWidgets

# Configura modo offscreen
os.environ["QT_QPA_PLATFORM"] = "offscreen"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ui.core.config import ConfigManager
from ui.core.i18n import I18nManager, tr
from ui.core.screens.dock_settings_dialog import DockBarsSettingsDialog
from ui.core.screens.floating_toolbar_settings_dialog import FloatingToolbarSettingsDialog
from ui.core.screens.settings.theme_dialog import ThemeDialog
from ui.core.dialogs.render_settings_dialog import RenderSettingsDialog
from ui.core.screens.cursor_settings_dialog import CursorSettingsDialog
from ui.core.screens.keyboard_shortcuts_dialog import KeyboardShortcutsDialog
from plugins.system.workspace_core.workspace.secondary_tool_bar.toolbar import SecondaryToolBar


class TestDialogsI18nRetranslation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def setUp(self):
        ConfigManager.instance().set_test_mode(True)
        self.i18n = I18nManager.instance()
        self.i18n.set_locale("pt_BR", is_auto=False)

    def tearDown(self):
        self.i18n.set_locale("pt_BR", is_auto=False)
        ConfigManager.instance().set_test_mode(False)

    def test_01_dock_settings_dialog_retranslation(self):
        """Valida que o diálogo de gavetas traduz títulos, labels e combos dinamicamente."""
        dialog = DockBarsSettingsDialog()
        try:
            # pt_BR
            self.assertEqual(dialog.lbl_behavior.text(), "Comportamento")
            self.assertEqual(dialog.lbl_collapse.text(), "Auto-Recolhimento:")
            self.assertEqual(dialog.cbo_speed.itemText(0), "Ultra Rápido")
            self.assertEqual(dialog.btn_apply.text(), "Aplicar")

            # Troca para en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertEqual(dialog.lbl_behavior.text(), "Behavior")
            self.assertEqual(dialog.lbl_collapse.text(), "Auto-Collapse:")
            self.assertEqual(dialog.cbo_speed.itemText(0), "Ultra Fast")
            self.assertEqual(dialog.btn_apply.text(), "Apply")

            # Troca para ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertEqual(dialog.lbl_behavior.text(), "動作設定")
            self.assertEqual(dialog.lbl_collapse.text(), "自動格納:")
            self.assertEqual(dialog.cbo_speed.itemText(0), "超高速")
            self.assertEqual(dialog.btn_apply.text(), "適用")
        finally:
            dialog.deleteLater()

    def test_02_floating_toolbar_settings_dialog_retranslation(self):
        """Valida que o diálogo da barra flutuante e seus cartões de ferramentas re-traduzem."""
        dialog = FloatingToolbarSettingsDialog()
        try:
            # pt_BR
            self.assertEqual(dialog.lbl_insp_title.text(), "Barra Rápida Flutuante")
            self.assertEqual(dialog.search_box.placeholderText(), "Buscar ferramenta...")
            self.assertEqual(dialog.btn_apply.text(), "Salvar e Aplicar")

            # en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertEqual(dialog.lbl_insp_title.text(), "Floating Quick Toolbar")
            self.assertEqual(dialog.search_box.placeholderText(), "Search tool...")
            self.assertEqual(dialog.btn_apply.text(), "Save & Apply")
            self.assertEqual(dialog.combo_speed.itemText(0), "Disabled (Always Visible)")

            # Verifica se os cartões de ferramentas foram traduzidos
            if dialog._cards:
                first_card = dialog._cards[0]
                self.assertTrue(len(first_card.name_lbl.text()) > 0)
                if first_card.meta.get("shortcut"):
                    self.assertTrue("Shortcut:" in first_card.shortcut_lbl.text())

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertEqual(dialog.lbl_insp_title.text(), "フローティングクイックツールバー")
            self.assertEqual(dialog.search_box.placeholderText(), "ツールを検索...")
            self.assertEqual(dialog.btn_apply.text(), "保存して適用")
            self.assertEqual(dialog.combo_speed.itemText(0), "無効 (常に表示)")
            if dialog._cards:
                first_card = dialog._cards[0]
                if first_card.meta.get("shortcut"):
                    self.assertTrue("ショートカット:" in first_card.shortcut_lbl.text())
        finally:
            dialog.deleteLater()

    def test_03_theme_dialog_retranslation(self):
        """Valida que o diálogo de temas traduz filtros, busca e botões."""
        dialog = ThemeDialog()
        try:
            # pt_BR
            self.assertEqual(dialog.search_box.placeholderText(), "Buscar tema...")
            self.assertEqual(dialog.combo_filter.itemText(0), "Todos os Temas")
            self.assertEqual(dialog.btn_close.text(), "Fechar")

            # en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertEqual(dialog.search_box.placeholderText(), "Search theme...")
            self.assertEqual(dialog.combo_filter.itemText(0), "All Themes")
            self.assertEqual(dialog.combo_filter.itemText(1), "Dark Themes")
            self.assertEqual(dialog.btn_close.text(), "Close")

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertEqual(dialog.search_box.placeholderText(), "テーマを検索...")
            self.assertEqual(dialog.combo_filter.itemText(0), "すべてのテーマ")
            self.assertEqual(dialog.combo_filter.itemText(1), "ダークテーマ")
            self.assertEqual(dialog.btn_close.text(), "閉じる")
        finally:
            dialog.deleteLater()

    def test_04_render_settings_dialog_retranslation(self):
        """Valida que o diálogo de configurações de renderização traduz categorias e busca."""
        dialog = RenderSettingsDialog()
        try:
            # pt_BR
            self.assertEqual(dialog.combo_cat.itemText(0), "Todas as Categorias")
            self.assertEqual(dialog.search_box.placeholderText(), "Buscar perfil...")
            self.assertEqual(dialog.btn_apply.text(), "Aplicar Perfil ao Canvas")

            # en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertEqual(dialog.combo_cat.itemText(0), "All Categories")
            self.assertEqual(dialog.search_box.placeholderText(), "Search profile...")
            self.assertEqual(dialog.btn_apply.text(), "Apply Profile to Canvas")

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertEqual(dialog.combo_cat.itemText(0), "すべてのカテゴリ")
            self.assertEqual(dialog.search_box.placeholderText(), "プロファイルを検索...")
            self.assertEqual(dialog.btn_apply.text(), "キャンバスにプロファイルを適用")
        finally:
            dialog.deleteLater()

    def test_05_cursor_and_shortcuts_dialog_retranslation(self):
        """Valida telas de cursor e atalhos de teclado reagindo ao idioma."""
        cur_dialog = CursorSettingsDialog()
        short_dialog = KeyboardShortcutsDialog()
        try:
            # Cursor Dialog en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertEqual(cur_dialog.lbl_title.text(), "Cursor & Pointer Settings")
            self.assertEqual(cur_dialog.btn_restore.text(), "Restore Defaults")
            self.assertEqual(cur_dialog.btn_save.text(), "Save & Apply")

            # Shortcuts Dialog en_US
            self.assertEqual(short_dialog.lbl_title.text(), "Keyboard Shortcuts")
            self.assertEqual(short_dialog.btn_restore.text(), "Restore Defaults")
            self.assertEqual(short_dialog.category_names[0][1], "All")

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertEqual(cur_dialog.lbl_title.text(), "カーソル設定")
            self.assertEqual(cur_dialog.btn_restore.text(), "初期設定に戻す")
            self.assertEqual(cur_dialog.btn_save.text(), "保存して適用")

            self.assertEqual(short_dialog.lbl_title.text(), "ショートカットキー設定")
            self.assertEqual(short_dialog.btn_restore.text(), "初期設定に戻す")
            self.assertEqual(short_dialog.category_names[0][1], "すべて")
        finally:
            cur_dialog.deleteLater()
            short_dialog.deleteLater()

    def test_06_secondary_toolbar_retranslation(self):
        """Valida que a barra de ferramentas secundária re-traduz opções dinamicamente."""
        tb = SecondaryToolBar()
        try:
            # en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertEqual(tb.cbo_sample_h.itemText(0), "1x1 Point Sample")
            self.assertEqual(tb.btn_eye_merged_h.text(), "All Layers")
            self.assertEqual(tb.btn_bkt_contig_h.text(), "Contiguous")
            self.assertEqual(tb.btn_wand_contig_h.text(), "Contiguous")

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertEqual(tb.cbo_sample_h.itemText(0), "1x1 ポイント")
            self.assertEqual(tb.btn_eye_merged_h.text(), "すべてのレイヤー")
            self.assertEqual(tb.btn_bkt_contig_h.text(), "隣接")
            self.assertEqual(tb.btn_wand_contig_h.text(), "隣接")

            # pt_BR
            self.i18n.set_locale("pt_BR", is_auto=False)
            self.assertEqual(tb.cbo_sample_h.itemText(0), "1x1 Ponto Único")
            self.assertEqual(tb.btn_eye_merged_h.text(), "Todas as Camadas")
            self.assertEqual(tb.btn_bkt_contig_h.text(), "Contíguo")
            self.assertEqual(tb.btn_wand_contig_h.text(), "Contíguo")
        finally:
            tb.deleteLater()

    def test_07_settings_menu_retranslation(self):
        """Valida que o menu de Configurações da MenuBar traduz todas as suas opções dinamicamente."""
        from ui.core.components.menu_bar.menu_bar import MenuBar
        mb = MenuBar()
        try:
            # en_US
            self.i18n.set_locale("en_US", is_auto=False)
            mb.retranslate_ui()
            self.assertEqual(mb.settings_menu.title(), "Settings")
            self.assertEqual(mb.language_menu.title(), "Language")
            self.assertEqual(mb.act_render.text(), "Rendering & Color Modes...")
            self.assertEqual(mb.act_curves.text(), "LUT Curves (Brush Profiles)...")
            self.assertEqual(mb.act_cursor.text(), "Cursor & Pointer Settings...")
            self.assertEqual(mb.act_shortcuts.text(), "Keyboard Shortcuts...")
            self.assertEqual(mb.act_theme.text(), "Theme Customization...")
            self.assertEqual(mb.act_plugins.text(), "Plugin Manager...")

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            mb.retranslate_ui()
            self.assertEqual(mb.settings_menu.title(), "設定")
            self.assertEqual(mb.act_render.text(), "レンダリングとカラーモード...")
            self.assertEqual(mb.act_theme.text(), "テーマのカスタマイズ...")
            self.assertEqual(mb.act_plugins.text(), "プラグインマネージャー...")

            # pt_BR
            self.i18n.set_locale("pt_BR", is_auto=False)
            mb.retranslate_ui()
            self.assertEqual(mb.settings_menu.title(), "Configurações")
            self.assertEqual(mb.act_render.text(), "Renderização & Modos de Cor...")
            self.assertEqual(mb.act_theme.text(), "Personalização de Tema...")
            self.assertEqual(mb.act_plugins.text(), "Gerenciador de Plugins...")
        finally:
            mb.deleteLater()

    def test_08_geometry_panel_icon_and_retranslation(self):
        """Valida que o GeometryPanel possui ícone SVG na engrenagem e re-traduz o status idle dinamicamente."""
        from plugins.ui.geometry_plugin.panel import GeometryPanel
        panel = GeometryPanel()
        try:
            # Verifica que o botão de configurações possui ícone SVG válido
            self.assertFalse(panel.btn_advanced.icon().isNull())
            self.assertEqual(panel.btn_advanced.text(), "")

            # pt_BR
            self.i18n.set_locale("pt_BR", is_auto=False)
            self.assertEqual(panel.lbl_status.text(), "Selecione um modo de régua ou simetria acima para iniciar o desenho assistido.")

            # en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertEqual(panel.lbl_status.text(), "Select a ruler or symmetry mode above to begin assisted drawing.")

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertEqual(panel.lbl_status.text(), "上の定規または対称モードを選択してアシスト描画を開始します。")
        finally:
            panel.deleteLater()

    def test_09_advanced_geometry_dialog_retranslation(self):
        """Valida que o diálogo avançado de geometria re-traduz as 3 abas e todos os seus controles."""
        from plugins.ui.geometry_plugin.components.advanced_settings_dialog import AdvancedGeometryDialog
        dialog = AdvancedGeometryDialog()
        try:
            # en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertEqual(dialog.tab_bar.tabText(0), "6P Perspective")
            self.assertEqual(dialog.tab_bar.tabText(1), "Snapping & Guides")
            self.assertEqual(dialog.tab_bar.tabText(2), "Symmetry")
            # Tab 0
            self.assertEqual(dialog.sec_cam._title_lbl.text(), "3D CAMERA & DISTORTION")
            self.assertEqual(dialog.slider_yaw.core.prefix, "Yaw:")
            self.assertEqual(dialog.sec_grid._title_lbl.text(), "CURVILINEAR GRID & ELEMENTS")
            self.assertEqual(dialog.lbl_d.text(), "Density:")
            self.assertEqual(dialog.combo_density.itemText(0), "Fine (15°)")
            self.assertEqual(dialog.chk_ring.text(), "Boundaries (180°)")
            self.assertEqual(dialog.chk_cube.text(), "3D Cube")
            # Tab 1
            self.assertEqual(dialog.sec_snap._title_lbl.text(), "MODE & SENSITIVITY")
            self.assertEqual(dialog.lbl_m.text(), "Snap Axis:")
            self.assertEqual(dialog.combo_snap_mode.itemText(0), "Auto (All Guides)")
            self.assertEqual(dialog.slider_sens.core.prefix, "Sensit:")
            self.assertEqual(dialog.sec_draw._title_lbl.text(), "DRAWING BEHAVIOR")
            self.assertEqual(dialog.chk_dynamic.text(), "Enable Dynamic Snap (Freehand)")
            # Tab 2
            self.assertEqual(dialog.sec_axes._title_lbl.text(), "AXES & ANGLE")
            self.assertEqual(dialog.slider_seg.core.prefix, "Segments:")
            self.assertEqual(dialog.slider_ang.core.prefix, "Angle:")
            self.assertEqual(dialog.sec_rest._title_lbl.text(), "PAINT RESTRICTIONS")
            self.assertEqual(dialog.chk_stop.text(), "Stop stroke at center (Stop-at-Center)")
            self.assertEqual(dialog.chk_lock.text(), "Lock center position on canvas")

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertEqual(dialog.tab_bar.tabText(0), "6点透視パース")
            self.assertEqual(dialog.tab_bar.tabText(1), "スナップ＆ガイド")
            self.assertEqual(dialog.tab_bar.tabText(2), "対称設定")
            self.assertEqual(dialog.sec_cam._title_lbl.text(), "3Dカメラと歪み")
            self.assertEqual(dialog.slider_yaw.core.prefix, "ヨー角 (Yaw):")
            self.assertEqual(dialog.lbl_d.text(), "密度:")
            self.assertEqual(dialog.combo_density.itemText(0), "細 (15°)")
            self.assertEqual(dialog.chk_ring.text(), "境界 (180°)")
            self.assertEqual(dialog.sec_snap._title_lbl.text(), "モードと感度")
            self.assertEqual(dialog.lbl_m.text(), "スナップ軸:")
            self.assertEqual(dialog.combo_snap_mode.itemText(0), "自動 (すべてのガイド)")
            self.assertEqual(dialog.slider_sens.core.prefix, "感度:")
            self.assertEqual(dialog.sec_axes._title_lbl.text(), "軸と角度")
            self.assertEqual(dialog.slider_seg.core.prefix, "セグメント:")

            # pt_BR
            self.i18n.set_locale("pt_BR", is_auto=False)
            self.assertEqual(dialog.tab_bar.tabText(0), "Perspectiva 6P")
            self.assertEqual(dialog.tab_bar.tabText(1), "Snapping & Guias")
            self.assertEqual(dialog.tab_bar.tabText(2), "Simetria")
            self.assertEqual(dialog.sec_cam._title_lbl.text(), "CÂMERA 3D & DISTORÇÃO")
            self.assertEqual(dialog.slider_yaw.core.prefix, "Yaw:")
            self.assertEqual(dialog.sec_grid._title_lbl.text(), "GRADE CURVILÍNEA & ELEMENTOS")
            self.assertEqual(dialog.lbl_d.text(), "Densidade:")
            self.assertEqual(dialog.combo_density.itemText(0), "Fina (15°)")
            self.assertEqual(dialog.chk_ring.text(), "Limites (180°)")
            self.assertEqual(dialog.sec_snap._title_lbl.text(), "MODO & SENSIBILIDADE")
            self.assertEqual(dialog.lbl_m.text(), "Eixo de Snap:")
            self.assertEqual(dialog.combo_snap_mode.itemText(0), "Auto (Todas as Guias)")
            self.assertEqual(dialog.sec_axes._title_lbl.text(), "EIXOS & ÂNGULO")
            self.assertEqual(dialog.slider_seg.core.prefix, "Segmentos:")
        finally:
            dialog.deleteLater()

    def test_10_theme_dialog_dropdowns_and_labels_retranslation(self):
        """Valida que o ThemeDialog re-traduz o grupo de ajustes, labels e itens de dropdowns."""
        from ui.core.screens.settings.theme_dialog import ThemeDialog
        dialog = ThemeDialog()
        try:
            # en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertEqual(dialog.tweaks_group.title(), "Fine Tuning (Geometry & Typography)")
            self.assertEqual(dialog.lbl_rad.text(), "Corner Radius:")
            self.assertEqual(dialog.lbl_fnt.text(), "Font Family:")
            self.assertIn("Square", dialog.combo_radius.itemText(1))

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertEqual(dialog.lbl_rad.text(), "角丸の半径:")
            self.assertEqual(dialog.lbl_fnt.text(), "フォントファミリー:")

            # pt_BR
            self.i18n.set_locale("pt_BR", is_auto=False)
            self.assertEqual(dialog.lbl_rad.text(), "Raio dos Cantos:")
            self.assertEqual(dialog.lbl_fnt.text(), "Família da Fonte:")
            self.assertIn("Quadrado", dialog.combo_radius.itemText(1))
        finally:
            dialog.deleteLater()

    def test_11_telemetry_panel_and_diagnostics_dialog_retranslation(self):
        """Valida que o TelemetryPanel e o TelemetryDiagnosticsDialog re-traduzem dinamicamente."""
        from plugins.ui.telemetry_plugin.panel import TelemetryPanel
        from ui.core.dialogs.telemetry_diagnostics_dialog import TelemetryDiagnosticsDialog

        panel = TelemetryPanel()
        diag = TelemetryDiagnosticsDialog()
        try:
            # en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertIn("Enable Telemetry Capture", panel.btn_toggle_telemetry.text())
            self.assertIn("Idle", panel.lbl_status.text())
            self.assertEqual(diag.tabs.tabText(0), "📈 Performance")
            self.assertEqual(diag.tabs.tabText(1), "🧠 Memory & Tiles")
            self.assertEqual(diag.btn_close.text(), "Close")

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertIn("テレメトリ計測を有効化", panel.btn_toggle_telemetry.text())
            self.assertIn("待機中", panel.lbl_status.text())
            self.assertEqual(diag.tabs.tabText(0), "📈 パフォーマンス")
            self.assertEqual(diag.tabs.tabText(1), "🧠 メモリとタイル")
            self.assertEqual(diag.btn_close.text(), "閉じる")

            # pt_BR
            self.i18n.set_locale("pt_BR", is_auto=False)
            self.assertIn("Ativar Captura de Telemetria", panel.btn_toggle_telemetry.text())
            self.assertIn("Em Espera", panel.lbl_status.text())
            self.assertEqual(diag.tabs.tabText(0), "📈 Desempenho")
            self.assertEqual(diag.tabs.tabText(1), "🧠 Memória & Tiles")
            self.assertEqual(diag.btn_close.text(), "Fechar")
        finally:
            panel.deleteLater()
            diag.deleteLater()

    def test_12_secondary_toolbar_shapes_transform_selection_retranslation(self):
        """Valida que formas, transformação e seleções da barra secundária re-traduzem."""
        from plugins.system.workspace_core.workspace.secondary_tool_bar.toolbar import SecondaryToolBar
        tb = SecondaryToolBar()
        try:
            # en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertEqual(tb.lbl_shape_stroke_h.text(), "Stroke:")
            self.assertEqual(tb.lbl_shape_border_h.text(), "Border:")
            self.assertEqual(tb.lbl_shape_fill_h.text(), "Fill:")
            self.assertEqual(tb.btn_trans_aspect_h.text(), "Lock Aspect")
            self.assertEqual(tb.btn_geom_deselect_h.text().strip(), "Deselect")

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertEqual(tb.lbl_shape_stroke_h.text(), "線の太さ:")
            self.assertEqual(tb.lbl_shape_border_h.text(), "輪郭:")
            self.assertEqual(tb.lbl_shape_fill_h.text(), "塗り:")
            self.assertEqual(tb.btn_trans_aspect_h.text(), "縦横比を固定")
            self.assertEqual(tb.btn_geom_deselect_h.text().strip(), "選択解除")

            # pt_BR
            self.i18n.set_locale("pt_BR", is_auto=False)
            self.assertEqual(tb.lbl_shape_stroke_h.text(), "Traço:")
            self.assertEqual(tb.lbl_shape_border_h.text(), "Borda:")
            self.assertEqual(tb.lbl_shape_fill_h.text(), "Fundo:")
            self.assertEqual(tb.btn_trans_aspect_h.text(), "Travar Proporção")
            self.assertEqual(tb.btn_geom_deselect_h.text().strip(), "Desmarcar")
        finally:
            tb.deleteLater()

    def test_13_menubar_dialogs_retranslation(self):
        """Valida que todos os demais diálogos da MenuBar re-traduzem dinamicamente."""
        from ui.core.screens.curve_window import CurveWindow
        from ui.core.screens.plugins.dialog import PluginsWindow
        from ui.core.dialogs.canvas_size_dialog import CanvasSizeDialog
        from ui.core.dialogs.layer_properties_dialog import LayerPropertiesDialog
        from ui.core.dialogs.modify_selection_dialog import ModifySelectionDialog
        from ui.core.dialogs.diagnostics_dialog import DiagnosticsDialog
        from ui.core.screens.about_dialog import AboutDialog
        from ui.core.screens.filters.filter_adjustment_dialog import FilterAdjustmentDialog

        cw = CurveWindow()
        pw = PluginsWindow()
        cs = CanvasSizeDialog(current_w=800, current_h=600)
        lp = LayerPropertiesDialog(name="Layer 1")
        ms = ModifySelectionDialog(mode="expand")
        dd = DiagnosticsDialog()
        ab = AboutDialog()
        fa = FilterAdjustmentDialog()

        try:
            # en_US
            self.i18n.set_locale("en_US", is_auto=False)
            self.assertEqual(cw.windowTitle(), "Profiles & LUT Curves")
            self.assertEqual(pw.windowTitle(), "Plugin Manager")
            self.assertEqual(cs.windowTitle(), "Canvas Size...")
            self.assertEqual(lp.windowTitle(), "Layer Properties")
            self.assertEqual(ms.windowTitle(), "Expand Selection...")
            self.assertEqual(dd.windowTitle(), "Engine Diagnostics & Telemetry")
            self.assertEqual(ab.windowTitle(), "About Lumenia Art Studio")
            self.assertEqual(fa.windowTitle(), "Filter Gallery")

            # ja_JP
            self.i18n.set_locale("ja_JP", is_auto=False)
            self.assertEqual(cw.windowTitle(), "プロファイルとLUTカーブ")
            self.assertEqual(pw.windowTitle(), "プラグインマネージャー")
            self.assertEqual(cs.windowTitle(), "キャンバスサイズ...")
            self.assertEqual(lp.windowTitle(), "レイヤープロパティ")
            self.assertEqual(ms.windowTitle(), "選択範囲を拡大...")
            self.assertEqual(dd.windowTitle(), "エンジンの診断とテレメトリ")
            self.assertEqual(ab.windowTitle(), "Lumenia について")
            self.assertEqual(fa.windowTitle(), "フィルターギャラリー")

            # pt_BR
            self.i18n.set_locale("pt_BR", is_auto=False)
            self.assertEqual(cw.windowTitle(), "Perfis & Curvas LUT")
            self.assertEqual(pw.windowTitle(), "Gerenciador de Plugins")
            self.assertEqual(cs.windowTitle(), "Tamanho do Canvas...")
            self.assertEqual(lp.windowTitle(), "Propriedades da Camada")
            self.assertEqual(ms.windowTitle(), "Expandir Seleção...")
            self.assertEqual(dd.windowTitle(), "Diagnóstico & Telemetria do Motor")
            self.assertEqual(ab.windowTitle(), "Sobre o Lumenia")
            self.assertEqual(fa.windowTitle(), "Galeria de Filtros")
        finally:
            cw.deleteLater()
            pw.deleteLater()
            cs.deleteLater()
            lp.deleteLater()
            ms.deleteLater()
            dd.deleteLater()
            ab.deleteLater()
            fa.deleteLater()


if __name__ == "__main__":
    unittest.main()
