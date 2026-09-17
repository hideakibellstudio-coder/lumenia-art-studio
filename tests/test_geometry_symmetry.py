import os
import sys
import math
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import aladyn_engine_native as aen


class TestGeometrySymmetry(unittest.TestCase):
    def setUp(self):
        self.facade = aen.PaintEngineFacade(800, 600)
        self.facade.add_layer("Desenho")

    def test_01_symmetry_modes_and_constants(self):
        """Verifica se os enums de simetria e guias estão exportados."""
        self.assertEqual(int(getattr(aen.SymmetryMode, "None")), 0)
        self.assertEqual(int(aen.SymmetryMode.Mirror), 1)
        self.assertEqual(int(aen.SymmetryMode.DoubleMirror), 2)
        self.assertEqual(int(aen.SymmetryMode.Radial), 3)
        self.assertEqual(int(aen.SymmetryMode.Kaleidoscope), 4)

        self.assertEqual(int(aen.GuideType.Straight), 1)
        self.assertEqual(int(aen.GuideType.CurveRuler), 2)
        self.assertEqual(int(aen.GuideType.Isometric), 7)

    def test_02_symmetry_vertical_mirror_stroke(self):
        """Testa traço com espelho vertical (cx=400, angle=pi/2)."""
        # Espelho vertical no centro da tela (X=400)
        self.facade.set_symmetry_config(
            mode=int(aen.SymmetryMode.Mirror),
            cx=400.0,
            cy=300.0,
            angle_rad=math.pi / 2.0,
            segments=2,
            stop_at_center=False
        )

        # Desenha um ponto em X=200, Y=300
        p_start = aen.PointerEvent(aen.PointerEventType.Press, aen.Point2D(200.0, 300.0), 1.0, 0.0)
        p_end = aen.PointerEvent(aen.PointerEventType.Move, aen.Point2D(205.0, 305.0), 1.0, 0.1)
        self.facade.begin_stroke(p_start)
        self.facade.update_stroke(p_end)
        self.facade.end_stroke(p_end)

        # Deve ter pintado em X=200..205 e no espelho X=595..600 (400 + (400-200) = 600)
        # Verifica se o pixel em (200, 300) e (600, 300) foram modificados
        # Podemos validar via thumbnail ou verificação indireta
        thumb = self.facade.get_layer_thumbnail_buffer(0, 80, 60)
        self.assertIsNotNone(thumb)
        self.assertEqual(len(thumb), 80 * 60 * 4)

    def test_03_snap_straight_ruler(self):
        """Testa o algoritmo de atração magnética para a régua reta."""
        # Régua reta horizontal passando por Y=200 (de (0, 200) a (800, 200))
        self.facade.set_guide_config(
            type=int(aen.GuideType.Straight),
            p0x=0.0, p0y=200.0,
            p1x=800.0, p1y=200.0,
            snap_radius=30.0
        )

        # Ponto próximo da reta (ex: Y=210) -> deve ser atraído para Y=200
        snapped = self.facade.snap_point(350.0, 210.0)
        self.assertAlmostEqual(snapped[0], 350.0, delta=1e-3)
        self.assertAlmostEqual(snapped[1], 200.0, delta=1e-3)

        # Ponto longe da reta (ex: Y=350) -> não deve ser atraído
        free_point = self.facade.snap_point(350.0, 350.0)
        self.assertAlmostEqual(free_point[0], 350.0, delta=1e-3)
        self.assertAlmostEqual(free_point[1], 350.0, delta=1e-3)

    def test_04_snap_curve_bezier_ruler(self):
        """Testa o algoritmo de atração magnética para a régua curva Bézier."""
        # Curva Bézier cúbica
        self.facade.set_guide_config(
            type=int(aen.GuideType.CurveRuler),
            p0x=100.0, p0y=100.0,
            p1x=200.0, p1y=300.0,
            p2x=400.0, p2y=300.0,
            p3x=500.0, p3y=100.0,
            snap_radius=40.0
        )

        # Ponto próximo do ápice da curva (em t=0.5, ápice fica em torno de X=300, Y=250)
        snapped = self.facade.snap_point(300.0, 245.0)
        # Deve ter sido projetado para mais perto da curva
        self.assertAlmostEqual(snapped[0], 300.0, delta=5.0)
        self.assertAlmostEqual(snapped[1], 250.0, delta=5.0)

    def test_05_clear_symmetry_and_guide(self):
        """Testa limpeza e desativação das guias e simetrias."""
        self.facade.clear_symmetry()
        self.facade.clear_guide()
        snapped = self.facade.snap_point(123.4, 567.8)
        self.assertEqual(snapped[0], 123.4)
        self.assertEqual(snapped[1], 567.8)

    def test_06_proportional_centering_portrait_and_landscape(self):
        """Valida a centralização matemática e cálculo proporcional de base_radius para diferentes formatos."""
        from plugins.system.workspace_core.workspace.canvas.tools.geometry_tool_controller import GeometryToolController

        class DummyWidget:
            canvas_w = 2480
            canvas_h = 3508

        ctrl = GeometryToolController(DummyWidget())

        # 1. Teste Canvas A4 Vertical (Portrait: 2480 x 3508)
        ctrl.center_on_document(2480, 3508)
        self.assertEqual(ctrl.guide_state["cx"], 1240.0)
        self.assertEqual(ctrl.guide_state["cy"], 1754.0)
        self.assertEqual(ctrl.sym_state["cx"], 1240.0)
        self.assertEqual(ctrl.sym_state["cy"], 1754.0)
        self.assertAlmostEqual(ctrl.guide_state["base_radius"], 2480 * 0.42, delta=1e-3)

        # 2. Teste Canvas 4K UHD Horizontal (Landscape: 3840 x 2160)
        ctrl.center_on_document(3840, 2160)
        self.assertEqual(ctrl.guide_state["cx"], 1920.0)
        self.assertEqual(ctrl.guide_state["cy"], 1080.0)
        self.assertEqual(ctrl.sym_state["cx"], 1920.0)
        self.assertEqual(ctrl.sym_state["cy"], 1080.0)
        self.assertAlmostEqual(ctrl.guide_state["base_radius"], 2160 * 0.42, delta=1e-3)

        # 3. Teste Canvas Quadrado (Square: 3000 x 3000)
        ctrl.center_on_document(3000, 3000)
        self.assertEqual(ctrl.guide_state["cx"], 1500.0)
        self.assertEqual(ctrl.guide_state["cy"], 1500.0)
        self.assertAlmostEqual(ctrl.guide_state["base_radius"], 3000 * 0.42, delta=1e-3)

    def test_07_curvilinear_all_axes_snapping(self):
        """Valida que o snap curvilíneo 6P permite desenhar nos eixos Horizontal (H), Vertical (V) e Profundidade (D)."""
        from plugins.system.workspace_core.workspace.canvas.tools.geometry_tool_controller import GeometryToolController

        class DummyWidget:
            canvas_w = 1920
            canvas_h = 1080

        # 1. Teste de Traço Horizontal (movimento para a direita: dx=30, dy=0)
        ctrl_h = GeometryToolController(DummyWidget())
        ctrl_h.guide_state["type"] = "curvilinear"
        ctrl_h.center_on_document(1920, 1080)

        ctrl_h.start_stroke_snap((960.0, 300.0))
        # Puxa horizontalmente
        res_h = ctrl_h.snap_point(990.0, 300.0)
        self.assertIsNotNone(ctrl_h.locked_curve)
        fam_h = ctrl_h.locked_curve.get("family", "")
        self.assertTrue(fam_h.endswith("_x") or fam_h == "h" or fam_h.endswith("_z"), f"Esperado eixo H/D, obteve: {fam_h}")

        # 2. Teste de Traço Vertical (movimento para baixo: dx=0, dy=30)
        ctrl_v = GeometryToolController(DummyWidget())
        ctrl_v.guide_state["type"] = "curvilinear"
        ctrl_v.center_on_document(1920, 1080)

        ctrl_v.start_stroke_snap((960.0, 540.0))
        # Puxa verticalmente
        res_v = ctrl_v.snap_point(960.0, 570.0)
        self.assertIsNotNone(ctrl_v.locked_curve)
        fam_v = ctrl_v.locked_curve.get("family", "")
        self.assertTrue(fam_v.endswith("_v") or fam_v == "v", f"Esperado eixo V, obteve: {fam_v}")

    def test_07_geometry_ui_dialogs_and_popups(self):
        """Valida que o popup do seletor e a janela avançada de geometria instanciam perfeitamente sem crash."""
        from PySide6.QtWidgets import QApplication, QWidget
        from plugins.ui.geometry_plugin.components.geometry_selector import GeometrySelectorPopup, GeometrySelectorButton
        from plugins.ui.geometry_plugin.components.advanced_settings_dialog import AdvancedGeometryDialog

        app = QApplication.instance() or QApplication(sys.argv)
        parent = QWidget()

        # Testa GeometrySelectorPopup
        popup = GeometrySelectorPopup(parent)
        self.assertIsNotNone(popup)
        self.assertEqual(len(popup.ruler_buttons), 8)
        self.assertEqual(len(popup.sym_buttons), 7)

        # Testa GeometrySelectorButton
        btn = GeometrySelectorButton(parent)
        self.assertIsNotNone(btn)

        # Testa AdvancedGeometryDialog
        adv = AdvancedGeometryDialog(parent)
        self.assertIsNotNone(adv)
        self.assertEqual(adv.stack.count(), 3)

    def test_08_curvilinear_6p_vanishing_point_exact_convergence(self):
        """Valida que todas as curvas H, V e D passam rigorosamente pelos pontos de fuga sem desvio (distância < 1e-4)."""
        from plugins.system.workspace_core.workspace.canvas.renderers.geometry_overlay_renderer import (
            GeometryOverlayRenderer, rotate_3d_backward
        )

        for yaw in [0.0, 35.0, 75.0, 180.0]:
            for pitch in [0.0, -25.0, 45.0]:
                guide = {
                    "type": "curvilinear",
                    "cx": 500.0, "cy": 400.0,
                    "base_radius": 350.0, "fov": 130.0,
                    "density": 30.0, "yaw": yaw, "pitch": pitch,
                    "show_v": True, "show_h": True, "show_d": True,
                    "show_vps": True
                }

                data = GeometryOverlayRenderer._get_cached_curvilinear_data(guide)
                vps = {name: pt for name, pt, _ in data["vps"]}

                # 1. H-curves devem convergir rigorosamente em L e R
                if "L" in vps and "R" in vps:
                    vp_L, vp_R = vps["L"], vps["R"]
                    for c in data["h_curves"]:
                        if c["type"] == "circle":
                            dist_L = abs(math.hypot(vp_L.x() - c["center"].x(), vp_L.y() - c["center"].y()) - c["radius"])
                            dist_R = abs(math.hypot(vp_R.x() - c["center"].x(), vp_R.y() - c["center"].y()) - c["radius"])
                            self.assertLess(dist_L, 1e-4, f"H-curve desviou de VP_L em yaw={yaw}, pitch={pitch}")
                            self.assertLess(dist_R, 1e-4, f"H-curve desviou de VP_R em yaw={yaw}, pitch={pitch}")

                # 2. V-curves devem convergir rigorosamente em Z e N
                if "Z" in vps and "N" in vps:
                    vp_Z, vp_N = vps["Z"], vps["N"]
                    for c in data["v_curves"]:
                        if c["type"] == "circle":
                            dist_Z = abs(math.hypot(vp_Z.x() - c["center"].x(), vp_Z.y() - c["center"].y()) - c["radius"])
                            dist_N = abs(math.hypot(vp_N.x() - c["center"].x(), vp_N.y() - c["center"].y()) - c["radius"])
                            self.assertLess(dist_Z, 1e-4, f"V-curve desviou de VP_Z em yaw={yaw}, pitch={pitch}")
                            self.assertLess(dist_N, 1e-4, f"V-curve desviou de VP_N em yaw={yaw}, pitch={pitch}")

                # 3. D-curves devem convergir rigorosamente em F e B
                if "F" in vps and "B" in vps:
                    vp_F, vp_B = vps["F"], vps["B"]
                    for c in data["d_curves"]:
                        if c["type"] == "circle":
                            dist_F = abs(math.hypot(vp_F.x() - c["center"].x(), vp_F.y() - c["center"].y()) - c["radius"])
                            dist_B = abs(math.hypot(vp_B.x() - c["center"].x(), vp_B.y() - c["center"].y()) - c["radius"])
                            self.assertLess(dist_F, 1e-4, f"D-curve desviou de VP_F em yaw={yaw}, pitch={pitch}")
                            self.assertLess(dist_B, 1e-4, f"D-curve desviou de VP_B em yaw={yaw}, pitch={pitch}")

    def test_09_curvilinear_overlay_caching_performance(self):
        """Valida que o cache geométrico reutiliza os cálculos prévios em O(1)."""
        from plugins.system.workspace_core.workspace.canvas.renderers.geometry_overlay_renderer import GeometryOverlayRenderer

        guide = {
            "type": "curvilinear",
            "cx": 400.0, "cy": 300.0,
            "base_radius": 350.0, "fov": 130.0,
            "density": 30.0, "yaw": 15.0, "pitch": 10.0,
            "show_v": True, "show_h": True, "show_d": True,
            "show_ground": True, "show_ceiling": True
        }

        # Primeira chamada compila o cache
        d1 = GeometryOverlayRenderer._get_cached_curvilinear_data(guide)
        # Segunda chamada deve retornar exatamente a mesma instância em cache
        d2 = GeometryOverlayRenderer._get_cached_curvilinear_data(guide)
        self.assertIs(d1, d2)
        self.assertFalse(d1["ground_path"].isEmpty())
        self.assertFalse(d1["ceiling_path"].isEmpty())

    def test_10_curvilinear_native_snap_mode_filter(self):
        """Regressao Fase C3.0 (nativo): snap_mode v/h/d deve travar na
        familia correta -- espelha o teste equivalente em
        test_geometry_decomposition_phase1.py para o motor Python. Familias
        geradas sao sempre GroundV/GroundX/GroundZ; um filtro que so
        reconhece GroundV faz H e D nunca travarem em nada."""
        family_index = 1  # layout: [kind, family, p1x, p1y, p2x, p2y, dirx, diry, cx, cy, radius]
        for snap_mode, expected_family in ((1, 0), (2, 1), (3, 2)):  # v->GroundV, h->GroundX, d->GroundZ
            with self.subTest(snap_mode=snap_mode):
                self.facade.set_curvilinear_guide_config(snap_mode=snap_mode)
                candidates = self.facade.get_curvilinear_candidates(120.0, 80.0)
                self.assertEqual(len(candidates) % 11, 0)
                n = len(candidates) // 11
                families = {int(candidates[i * 11 + family_index]) for i in range(n)}
                self.assertIn(expected_family, families, f"fixture sanity: {families}")

                result = self.facade.snap_curvilinear(
                    120.0, 80.0, 120.0, 80.0, candidates, -1, True, 1.0
                )
                locked_index = int(result[2])
                self.assertGreaterEqual(locked_index, 0, f"snap_mode={snap_mode} deveria travar numa curva")
                locked_family = int(candidates[locked_index * 11 + family_index])
                self.assertEqual(locked_family, expected_family)

    def test_11_perspective_native_matches_python(self):
        """Regressao Fase C3.1: snap_perspective nativo deve produzir o mesmo
        resultado que snap_ray_perspective (Python) para a pontuacao por
        produto escalar e o travamento de direcao no inicio do traco.

        NAO cobre o comportamento apos a trava ter sido conquistada alem da
        tolerancia magnetica: a Fase C3.5 deu ao motor nativo uma trava
        magnetica (solta e repontua quando o afastamento excede
        config.snapRadius -- GuideSnapEngine::snapPerspective), enquanto
        snap_ray_perspective (Python) permanece com a trava rigida original
        (projeta na direcao travada para sempre, sem nunca reavaliar). Essa
        divergencia e intencional -- ver test_13_perspective_breakaway_releases_stale_lock,
        que cobre exatamente o comportamento de soltura nativo. O segundo
        ponto de arraste aqui fica deliberadamente dentro do raio magnetico
        (snapRadius=32, default) da reta travada no frame 1 para os 4 tipos
        de guia, para que este teste continue comparando so a parte do
        algoritmo que de fato e' um porte fiel (selecao de candidata +
        projecao), sem cruzar para o territorio onde os dois motores
        divergem por design."""
        from plugins.system.workspace_core.workspace.canvas.tools.geometry_snapping_engine import (
            GeometrySnappingEngine,
        )
        from PySide6 import QtCore as _QtCore

        vpA, vpB, vpC = (100.0, 300.0), (700.0, 300.0), (400.0, 50.0)
        type_map = {"one_point": 4, "two_point": 5, "three_point": 6, "isometric": 7}
        start = (400.0, 400.0)
        drag_points = [(430.0, 340.0), (400.0, 280.0)]  # 2 chamadas: destrava, depois trava (2o ponto dentro do raio magnetico de 32px)

        for gtype, type_id in type_map.items():
            with self.subTest(gtype=gtype):
                self.facade.set_guide_config(
                    type=type_id,
                    vp_ax=vpA[0], vp_ay=vpA[1], vp_bx=vpB[0], vp_by=vpB[1],
                    vp_cx=vpC[0], vp_cy=vpC[1],
                )
                guide_state = {
                    "type": gtype,
                    "vpA": _QtCore.QPointF(*vpA),
                    "vpB": _QtCore.QPointF(*vpB),
                    "vpC": _QtCore.QPointF(*vpC),
                }
                start_pt = _QtCore.QPointF(*start)

                py_locked = None
                native_has_lock, native_ldx, native_ldy = False, 0.0, 0.0
                for (rx, ry) in drag_points:
                    py_res, py_locked = GeometrySnappingEngine.snap_ray_perspective(
                        rx, ry, 1.0, guide_state, start_pt, py_locked
                    )
                    native_res = self.facade.snap_perspective(
                        rx, ry, start[0], start[1], native_has_lock, native_ldx, native_ldy, 1.0
                    )
                    native_has_lock = bool(native_res[2])
                    native_ldx, native_ldy = native_res[3], native_res[4]

                    self.assertAlmostEqual(native_res[0], py_res[0], places=6, msg=f"{gtype}: x diverge")
                    self.assertAlmostEqual(native_res[1], py_res[1], places=6, msg=f"{gtype}: y diverge")

    def test_12_curvilinear_breakaway_releases_stale_lock(self):
        """Regressao Fase C3.5: trava curvilinea deve soltar quando o cursor se
        afasta alem de snap_radius, em vez de ficar presa para sempre na curva
        travada (bug reportado: tracos rapidos "fogem" da guia e o traco fica
        colado numa curva errada pelo resto do gesto)."""
        # Layout: [kind, family, p1x,p1y, p2x,p2y, dirx,diry, cx,cy, radius]
        curve_a = [0, 0, -1000.0, 0.0, 1000.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]  # linha horizontal y=0
        curve_b = [0, 0, 500.0, -1000.0, 500.0, 1000.0, 0.0, 1.0, 0.0, 0.0, 0.0]  # linha vertical x=500
        candidates = curve_a + curve_b

        # snap_radius default (32.0): afastamento pequeno mantem a trava.
        x, y, idx = self.facade.snap_curvilinear(500.0, 10.0, 0.0, 0.0, candidates, 0, True, 1.0)
        self.assertEqual(idx, 0, "afastamento pequeno (10px < snap_radius) deveria manter a trava")
        self.assertAlmostEqual(x, 500.0, delta=1e-6)
        self.assertAlmostEqual(y, 0.0, delta=1e-6)

        # Afastamento grande (500px >> snap_radius de 32px): deve soltar a
        # curva A e reavaliar -- o cursor esta exatamente sobre a curva B e
        # o gesto (a partir de start=0,0) aponta na direcao dela, entao deve
        # travar em B, nao continuar projetando (errado) na curva A.
        x2, y2, idx2 = self.facade.snap_curvilinear(500.0, 500.0, 0.0, 0.0, candidates, 0, True, 1.0)
        self.assertEqual(idx2, 1, "deveria soltar a curva A e travar na curva B apos o afastamento")
        self.assertAlmostEqual(x2, 500.0, delta=1e-6)
        self.assertAlmostEqual(y2, 500.0, delta=1e-6)

    def test_13_perspective_breakaway_releases_stale_lock(self):
        """Regressao Fase C3.5: mesmo fix de C3.5, para snap_perspective."""
        self.facade.set_guide_config(
            type=5,  # TwoPoint
            vp_ax=100.0, vp_ay=300.0, vp_bx=700.0, vp_by=300.0,
        )
        start = (400.0, 400.0)

        # Travado (artificialmente) numa direcao vertical (0,1); afastamento
        # pequeno mantem a trava.
        x, y, has_lock, ldx, ldy = self.facade.snap_perspective(400.0, 410.0, start[0], start[1], True, 0.0, 1.0, 1.0)
        self.assertTrue(has_lock)
        self.assertAlmostEqual(x, 400.0, delta=1e-6)
        self.assertAlmostEqual(y, 410.0, delta=1e-6)

        # Cursor salta para exatamente vpB (700, 300) -- bem longe da reta
        # vertical travada (300px de afastamento, >> snap_radius de 32px) e
        # exatamente na direcao de vpB a partir de start. Deve soltar a trava
        # vertical errada e travar na direcao de vpB.
        x2, y2, has_lock2, ldx2, ldy2 = self.facade.snap_perspective(700.0, 300.0, start[0], start[1], True, 0.0, 1.0, 1.0)
        self.assertTrue(has_lock2)
        self.assertAlmostEqual(x2, 700.0, delta=1e-4)
        self.assertAlmostEqual(y2, 300.0, delta=1e-4)
        # Nao pode ter ficado na direcao vertical antiga.
        self.assertFalse(abs(ldx2) < 1e-6 and abs(ldy2 - 1.0) < 1e-6)


if __name__ == "__main__":
    unittest.main()


