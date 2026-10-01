import unittest
import numpy as np

import aladyn_engine_native as aen
from ui.infrastructure.bridge_client.aladyn import AladynBackend


class TestViewportLODAntiAliasing(unittest.TestCase):
    """Bateria de testes de baixo nível para a Pirâmide Mipmap e Anti-Aliasing de Viewport."""

    def setUp(self):
        self.facade = aen.PaintEngineFacade(800, 600)
        self.facade.clear_canvas()

    def test_01_best_lod_level_and_scales(self):
        """Verifica a seleção matemática analítica dos níveis de LOD para cada faixa de zoom."""
        self.assertEqual(self.facade.get_best_lod_level(1.0), 0)
        self.assertEqual(self.facade.get_best_lod_level(0.8), 0)
        self.assertEqual(self.facade.get_best_lod_level(0.5), 1)
        self.assertEqual(self.facade.get_best_lod_level(0.38), 1)
        self.assertEqual(self.facade.get_best_lod_level(0.25), 2)
        self.assertEqual(self.facade.get_best_lod_level(0.20), 2)
        self.assertEqual(self.facade.get_best_lod_level(0.10), 3)
        self.assertEqual(self.facade.get_best_lod_level(0.02), 3)

        self.assertAlmostEqual(self.facade.get_lod_scale(0), 1.0)
        self.assertAlmostEqual(self.facade.get_lod_scale(1), 0.5)
        self.assertAlmostEqual(self.facade.get_lod_scale(2), 0.25)
        self.assertAlmostEqual(self.facade.get_lod_scale(3), 0.125)

    def test_02_buffer_lod_dimensions_and_downscale(self):
        """Valida que get_display_pixel_buffer_lod retorna buffers com dimensões exatas em potências de 2."""
        # Level 1: 400x300 (escala 0.5)
        res1 = self.facade.get_display_pixel_buffer_lod(1)
        self.assertIsNotNone(res1)
        mv1, w1, h1, scale1 = res1
        self.assertEqual(w1, 400)
        self.assertEqual(h1, 300)
        self.assertAlmostEqual(scale1, 0.5)
        self.assertEqual(len(mv1), 400 * 300 * 4)

        # Level 2: 200x150 (escala 0.25)
        res2 = self.facade.get_display_pixel_buffer_lod(2)
        self.assertIsNotNone(res2)
        mv2, w2, h2, scale2 = res2
        self.assertEqual(w2, 200)
        self.assertEqual(h2, 150)
        self.assertAlmostEqual(scale2, 0.25)
        self.assertEqual(len(mv2), 200 * 150 * 4)

        # Level 3: 100x75 (escala 0.125)
        res3 = self.facade.get_display_pixel_buffer_lod(3)
        self.assertIsNotNone(res3)
        mv3, w3, h3, scale3 = res3
        self.assertEqual(w3, 100)
        self.assertEqual(h3, 75)
        self.assertAlmostEqual(scale3, 0.125)
        self.assertEqual(len(mv3), 100 * 75 * 4)

    def test_03_antialiasing_box_filter_energy_conservation(self):
        """Valida que o Box Filter em C++ produz gradientes suaves contínuos sem corte binário."""
        self.facade.set_engine_type(int(aen.EngineType.Inker))
        profile = self.facade.get_brush_profile()
        profile.brush_size = 6.0
        profile.opacity = 1.0
        profile.base_color = aen.ColorRGBA(0, 0, 0, 255)

        self.facade.begin_stroke_raw(100.0, 300.0, 1.0)
        for i in range(1, 30):
            t = i / 30.0
            self.facade.update_stroke_raw(100.0 + 600.0 * t, 300.0, 1.0)
        self.facade.end_stroke_raw()

        # Requisita LOD 2 (1/4 de escala)
        res2 = self.facade.get_display_pixel_buffer_lod(2)
        self.assertIsNotNone(res2)
        mv2, w2, h2, _ = res2
        arr2 = np.frombuffer(mv2, dtype=np.uint8).reshape((h2, w2, 4))

        # A linha em y=300 no canvas original corresponde a y=75 no LOD 2
        line_slice = arr2[73:78, 100, 0] # Canal R dos pixels ao redor da linha
        min_val = np.min(line_slice)
        # O valor não deve ser preto estrito (0) nem branco puro (255), mas um tom suavizado de cinza
        self.assertGreater(min_val, 0, "O Box Filter deve suavizar o miolo da linha fina no nível reduzido")
        self.assertLess(min_val, 255, "A linha deve ser detectada no buffer reduzido")

        # Verifica se há transição gradual (anti-aliasing)
        unique_vals = len(np.unique(line_slice))
        self.assertGreaterEqual(unique_vals, 2, "Deve haver níveis intermediários de anti-aliasing")

    def test_04_aladyn_backend_get_display_image(self):
        """Verifica a integração com o AladynBackend e a entrega da imagem adaptativa ao zoom."""
        from PySide6.QtCore import QRect

        backend = AladynBackend()
        backend.init_renderer(0, 800, 600, 800, 600)
        whole = QRect(0, 0, 800, 600)

        # Zoom 100% -> escala 1.0
        display0 = backend.get_display_image(1.0, whole)
        self.assertIsNotNone(display0)
        self.assertAlmostEqual(display0.scale, 1.0)
        self.assertEqual(display0.image.width(), 800)
        self.assertEqual(display0.image.height(), 600)

        # Zoom 25% -> escala 0.25
        display2 = backend.get_display_image(0.25, whole)
        self.assertIsNotNone(display2)
        self.assertAlmostEqual(display2.scale, 0.25)
        self.assertEqual(display2.image.width(), 200)
        self.assertEqual(display2.image.height(), 150)


if __name__ == "__main__":
    unittest.main()
