"""
Low-Level Test Suite: Phase 3 - Giant Brushes, AVX2 SIMD Span Blender & Adaptive LOD
=====================================================================================
Validates:
1. Giant Brush Stability & Coverage (radii 250px to 400px / diameter up to 800px).
2. Solid Core SIMD Span Blending Fidelity (exact math on solid core, smooth fringe).
3. Adaptive LOD Step Scaling (continuous coverage without quadratic stamp explosion).
4. Spatial Culler & Circle-AABB Tile Culling on Massive Diameters.
"""

import os
import sys
import unittest
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import aladyn_engine_native as aen


class TestLowLevelPhase3GiantBrushesSimd(unittest.TestCase):
    def setUp(self):
        self.w = 800
        self.h = 800
        self.facade = aen.PaintEngineFacade(self.w, self.h)
        self.facade.set_background_visibility(False)
        self.facade.add_layer("Layer 1")
        self.facade.select_layer(0)

    def _get_canvas_array(self) -> np.ndarray:
        buf = self.facade.get_pixel_buffer()
        return np.frombuffer(buf, dtype=np.uint8).reshape((self.h, self.w, 4))

    # ── 1. Giant Brush Stability & Coverage ──────────────────────────────────
    def test_01_giant_brush_stroke_stability_and_coverage(self):
        """
        Valida a estabilidade e cobertura contínua de pincéis gigantes (raio 250px, diâmetro 500px).
        Garante ausência de falhas de memória, travamentos ou furos de rasterização.
        """
        profile = self.facade.get_brush_profile()
        profile.brush_size = 500.0  # Raio = 250px
        profile.hardness = 0.85
        profile.spacing_factor = 0.15
        profile.base_color = aen.ColorRGBA(40, 120, 220, 255)

        # Executa traço longo com pincel de 500px
        self.facade.begin_stroke_raw(250.0, 400.0, 1.0)
        for x in range(280, 551, 30):
            self.facade.update_stroke_raw(float(x), 400.0, 1.0)
        self.facade.end_stroke_raw()

        arr = self._get_canvas_array()
        # O centro do traço (400, 400) deve ser 100% sólido e opaco com a cor exata
        center = arr[400, 400]
        self.assertEqual(int(center[0]), 40, f"R deve ser 40, obtido {center[0]}")
        self.assertEqual(int(center[1]), 120, f"G deve ser 120, obtido {center[1]}")
        self.assertEqual(int(center[2]), 220, f"B deve ser 220, obtido {center[2]}")
        self.assertEqual(int(center[3]), 255, f"A deve ser 255, obtido {center[3]}")

        # Cobertura massiva: pelo menos 150.000 pixels pintados
        painted_count = int(np.sum(arr[:, :, 3] > 0))
        self.assertGreater(painted_count, 150000, f"Área pintada esperada > 150k, obtido {painted_count}")

    # ── 2. Solid Core SIMD Span Blending Fidelity ────────────────────────────
    def test_02_solid_core_simd_span_exact_math(self):
        """
        Valida que o particionamento do miolo sólido (SIMD Span Blender) produz
        exatamente a cor nominal nos pixels interiores e mantém transição suave na franja.
        """
        profile = self.facade.get_brush_profile()
        profile.brush_size = 100.0  # Raio = 50px
        profile.hardness = 0.8     # hardSpan = 40px
        profile.base_color = aen.ColorRGBA(255, 60, 30, 255)

        # Único dab no ponto (200, 200)
        self.facade.begin_stroke_raw(200.0, 200.0, 1.0)
        self.facade.end_stroke_raw()

        arr = self._get_canvas_array()

        # Miolo sólido (distância <= 35px do centro (200, 200)):
        # Todos os pixels devem ser puramente sólidos (255, 60, 30, 255)
        for dy in range(-30, 31, 5):
            for dx in range(-30, 31, 5):
                dist = np.sqrt(dx * dx + dy * dy)
                if dist <= 35.0:
                    px = arr[200 + dy, 200 + dx]
                    self.assertEqual(int(px[0]), 255, f"Solid core R mismatch em dx={dx}, dy={dy}")
                    self.assertEqual(int(px[1]), 60, f"Solid core G mismatch em dx={dx}, dy={dy}")
                    self.assertEqual(int(px[2]), 30, f"Solid core B mismatch em dx={dx}, dy={dy}")
                    self.assertEqual(int(px[3]), 255, f"Solid core A mismatch em dx={dx}, dy={dy}")

        # Exterior do dab (distância >= 55px): deve ser puramente transparente
        for dy in range(-70, 71, 10):
            for dx in range(-70, 71, 10):
                dist = np.sqrt(dx * dx + dy * dy)
                if dist >= 55.0:
                    px = arr[200 + dy, 200 + dx]
                    self.assertEqual(int(px[3]), 0, f"Pixel fora do dab não é transparente em dx={dx}, dy={dy}")

    # ── 3. Adaptive LOD Step Scaling & Continuous Coverage ───────────────────
    def test_03_adaptive_lod_continuous_coverage(self):
        """
        Valida que o Adaptive LOD em DabInterpolator ajusta o passo entre carimbos
        em pincéis gigantes sem deixar furos ou lacunas (gaps) na pintura contínua.
        """
        profile = self.facade.get_brush_profile()
        profile.brush_size = 400.0  # Raio = 200px
        profile.hardness = 0.5
        profile.spacing_factor = 0.25      # Espaçamento moderado
        profile.base_color = aen.ColorRGBA(10, 200, 100, 255)

        # Movimento diagonal rápido de (250, 250) a (550, 550) com passos espaçados
        self.facade.begin_stroke_raw(250.0, 250.0, 1.0)
        self.facade.update_stroke_raw(350.0, 350.0, 1.0)
        self.facade.update_stroke_raw(450.0, 450.0, 1.0)
        self.facade.update_stroke_raw(550.0, 550.0, 1.0)
        self.facade.end_stroke_raw()

        arr = self._get_canvas_array()
        # Amostra a linha diagonal central no corpo ativo do traço (350 a 540): nenhum pixel deve ter lacuna (alpha >= 200)
        for i in range(350, 541, 10):
            px = arr[i, i]
            self.assertGreaterEqual(int(px[3]), 200, f"Lacuna encontrada no traço em ({i}, {i}): alpha={px[3]}")

        # Garante cobertura contínua e substancial (mais de 100.000 pixels pintados)
        painted_count = int(np.sum(arr[:, :, 3] > 0))
        self.assertGreater(painted_count, 100000, f"Área esperada > 100k, obtido {painted_count}")

    # ── 4. Spatial Culler & Circle-AABB Tile Culling ─────────────────────────
    def test_04_giant_brush_spatial_culler_bounds(self):
        """
        Valida que mesmo com diâmetros gigantescos (pincel de 400px localizado no topo),
        o SpatialCuller e o Circle-AABB culling não tocam em micro-tiles distantes.
        """
        profile = self.facade.get_brush_profile()
        profile.brush_size = 400.0  # Raio = 200px
        profile.hardness = 0.9
        profile.base_color = aen.ColorRGBA(255, 255, 0, 255)

        # Pincel desenhado exclusivamente no canto superior esquerdo: (150, 150)
        self.facade.begin_stroke_raw(150.0, 150.0, 1.0)
        self.facade.end_stroke_raw()

        arr = self._get_canvas_array()
        # Região do quadrante inferior direito (600..750, 600..750) deve estar 100% vazia
        bottom_right = arr[600:750, 600:750, 3]
        self.assertEqual(int(np.sum(bottom_right)), 0, "Tiles do quadrante inferior direito não deveriam ser tocados")


if __name__ == "__main__":
    unittest.main()
