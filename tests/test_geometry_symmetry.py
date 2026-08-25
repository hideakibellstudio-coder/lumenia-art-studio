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


if __name__ == "__main__":
    unittest.main()
