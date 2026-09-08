#!/usr/bin/env python3
"""
Test Suite: Toolbars & Geometry I18n Retranslation
Valida se as opcoes da barra de ferramentas secundaria e dos paineis/dialogos de geometria
acompanham a mudanca de idioma em tempo real (pt_BR, en_US, es_ES, ja_JP).
"""

import os
import sys
import unittest
from PySide6 import QtWidgets

# Configura modo offscreen
os.environ["QT_QPA_PLATFORM"] = "offscreen"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ui.core.config import ConfigManager
from ui.core.i18n import I18nManager
from plugins.system.workspace_core.workspace.secondary_tool_bar.toolbar import SecondaryToolBar
from plugins.ui.geometry_plugin.panel import GeometryPanel
from plugins.ui.geometry_plugin.components.advanced_settings_dialog import AdvancedGeometryDialog


class TestToolbarsGeometryI18nRetranslation(unittest.TestCase):
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

    def test_01_secondary_toolbar_retranslation(self):
        """Valida que a barra de ferramentas secundaria re-traduz opcoes dinamicamente."""
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

    def test_02_secondary_toolbar_shapes_transform_selection_retranslation(self):
        """Valida que formas, transformacao e selecoes da barra secundaria re-traduzem."""
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

    def test_03_geometry_panel_icon_and_retranslation(self):
        """Valida que o GeometryPanel possui icone SVG na engrenagem e re-traduz o status idle dinamicamente."""
        panel = GeometryPanel()
        try:
            # Verifica que o botao de configuracoes possui icone SVG valido
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

    def test_04_advanced_geometry_dialog_retranslation(self):
        """Valida que o dialogo avancado de geometria re-traduz as 3 abas e todos os seus controles."""
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


if __name__ == "__main__":
    unittest.main()
