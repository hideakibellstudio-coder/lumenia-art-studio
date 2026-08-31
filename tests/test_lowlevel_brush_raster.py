"""
Low-Level Test Suite: Brush Engines & Pixel-Level Rasterization Fidelity
Validates that C++ paint engines rasterize pixels accurately to the active layer,
interpolate dabs continuously, respond to pressure curves, and erase cleanly.
"""

import os
import sys
import unittest
import numpy as np

# Raiz do projeto Lumenia
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import aladyn_engine_native as aen


class TestLowLevelBrushRaster(unittest.TestCase):
    def setUp(self):
        # Canvas de teste 200x200
        self.w = 200
        self.h = 200
        self.facade = aen.PaintEngineFacade(self.w, self.h)
        # Desativa o fundo de papel para testar o canal Alfa direto da camada
        self.facade.set_background_visibility(False)
        self.facade.add_layer("Desenho Teste")
        self.facade.select_layer(0)

    def _get_canvas_array(self) -> np.ndarray:
        """Retorna o buffer RGBA composto como array NumPy (H, W, 4) uint8."""
        buf = self.facade.get_pixel_buffer()
        return np.frombuffer(buf, dtype=np.uint8).reshape((self.h, self.w, 4))

    def _draw_line(self, x0, y0, x1, y1, steps=20, pressure=1.0):
        """Desenha uma linha reta simples via begin/update/end_stroke_raw com passos intermediários."""
        self.facade.begin_stroke_raw(float(x0), float(y0), pressure)
        for i in range(1, steps + 1):
            t = i / float(steps)
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            self.facade.update_stroke_raw(x, y, pressure)
        self.facade.end_stroke_raw()

    # ── 1. InkerEngine: Traço contínuo e escrita de pixels ────────────────────
    def test_01_inker_stroke_rasterization(self):
        """Valida se o InkerEngine grava pixels vermelhos opacos ao longo do traço."""
        self.facade.set_engine_type(int(aen.EngineType.Inker))
        profile = self.facade.get_brush_profile()
        profile.brush_size = 14.0
        profile.opacity = 1.0
        profile.base_color = aen.ColorRGBA(255, 0, 0, 255)  # Vermelho puro

        # Traço horizontal de (50, 100) a (150, 100)
        self._draw_line(50, 100, 150, 100, steps=25, pressure=1.0)

        arr = self._get_canvas_array()
        
        # O centro do traço em (100, 100) DEVE ser vermelho e opaco
        center_px = arr[100, 100]
        self.assertEqual(center_px[0], 255, f"R deve ser 255, obtido {center_px[0]}")
        self.assertEqual(center_px[1], 0, f"G deve ser 0, obtido {center_px[1]}")
        self.assertEqual(center_px[2], 0, f"B deve ser 0, obtido {center_px[2]}")
        self.assertGreaterEqual(center_px[3], 240, f"Alpha deve ser opaco, obtido {center_px[3]}")

        # Ponto longe do traço (50, 50) DEVE permanecer transparente (Alpha=0)
        outside_px = arr[50, 50]
        self.assertEqual(outside_px[3], 0, f"Ponto fora deve ter alpha 0, obtido {outside_px[3]}")

    # ── 2. EraserEngine: Limpeza e redução de Alpha ───────────────────────────
    def test_02_eraser_clears_painted_pixels(self):
        """Valida se o EraserEngine apaga traços anteriores reduzindo o canal alfa."""
        # 1. Pinta um bloco com Inker vermelho
        self.facade.set_engine_type(int(aen.EngineType.Inker))
        profile = self.facade.get_brush_profile()
        profile.brush_size = 20.0
        profile.opacity = 1.0
        profile.base_color = aen.ColorRGBA(255, 0, 0, 255)
        self._draw_line(80, 100, 120, 100, steps=15, pressure=1.0)

        arr_before = self._get_canvas_array()
        self.assertGreater(arr_before[100, 100, 3], 200, "Pixel antes do eraser deve ser opaco")

        # 2. Apaga sobre o centro com Eraser
        self.facade.set_engine_type(int(aen.EngineType.Eraser))
        profile = self.facade.get_brush_profile()
        profile.brush_size = 30.0
        profile.opacity = 1.0
        self._draw_line(95, 100, 105, 100, steps=15, pressure=1.0)

        arr_after = self._get_canvas_array()
        # O pixel apagado DEVE ter alpha reduzido/zerado
        self.assertLess(arr_after[100, 100, 3], 50, f"Pixel após eraser deve ter alpha baixo, obtido {arr_after[100, 100, 3]}")

    # ── 3. MarkerEngine: Acúmulo de pigmento e densidade ──────────────────────
    def test_03_marker_overlap_density(self):
        """Valida que múltiplas passadas do MarkerEngine aumentam a opacidade/densidade."""
        self.facade.set_engine_type(int(aen.EngineType.Marker))
        profile = self.facade.get_brush_profile()
        profile.brush_size = 15.0
        profile.spacing_factor = 0.4
        profile.opacity = 0.15
        profile.base_color = aen.ColorRGBA(0, 120, 255, 100)

        # Passada 1
        self._draw_line(50, 50, 150, 50, steps=8, pressure=0.5)
        arr1 = self._get_canvas_array()
        alpha_pass1 = int(arr1[50, 100, 3])

        # Passada 2 sobre a mesma linha
        self._draw_line(50, 50, 150, 50, steps=8, pressure=0.5)
        arr2 = self._get_canvas_array()
        alpha_pass2 = int(arr2[50, 100, 3])

        self.assertGreater(alpha_pass1, 0, "Passada 1 deve depositar pigmento")
        self.assertGreater(alpha_pass2, alpha_pass1, f"Passada 2 ({alpha_pass2}) deve ter mais pigmento que passada 1 ({alpha_pass1})")

    # ── 4. PencilEngine: Textura de grafite e rugosidade ──────────────────────
    def test_04_pencil_raster_and_dispersion(self):
        """Valida que o PencilEngine gera traço com dispersão de grafite."""
        self.facade.set_engine_type(int(aen.EngineType.Pencil))
        profile = self.facade.get_brush_profile()
        profile.brush_size = 12.0
        profile.opacity = 0.8
        profile.base_color = aen.ColorRGBA(30, 30, 30, 200)
        profile.pencil_params.graphite_hardness = 0.5

        self._draw_line(40, 40, 160, 40, steps=20, pressure=0.8)
        arr = self._get_canvas_array()

        center_px = arr[40, 100]
        self.assertGreater(center_px[3], 0, "Pencil deve gerar pixels visíveis")
        self.assertLess(center_px[0], 100)
        self.assertLess(center_px[1], 100)
        self.assertLess(center_px[2], 100)

    # ── 5. Watercolor & Oil: Motores artísticos ──────────────────────────────
    def test_05_watercolor_and_oil_switching(self):
        """Valida a troca a quente para Watercolor e Oil sem corromper memória."""
        # Watercolor
        self.facade.set_engine_type(int(aen.EngineType.Watercolor))
        profile = self.facade.get_brush_profile()
        profile.brush_size = 16.0
        profile.opacity = 0.7
        profile.base_color = aen.ColorRGBA(0, 200, 100, 255)
        self._draw_line(30, 80, 170, 80, steps=20, pressure=1.0)
        
        arr = self._get_canvas_array()
        self.assertGreater(arr[80, 100, 3], 0, "Watercolor deve pintar pixels")

        # Oil Impasto
        self.facade.set_engine_type(int(aen.EngineType.OilImpasto))
        profile = self.facade.get_brush_profile()
        profile.brush_size = 18.0
        profile.opacity = 0.9
        profile.base_color = aen.ColorRGBA(200, 100, 0, 255)
        self._draw_line(30, 120, 170, 120, steps=20, pressure=1.0)

        arr2 = self._get_canvas_array()
        self.assertGreater(arr2[120, 100, 3], 0, "Oil Impasto deve pintar pixels")

    # ── 6. Interpolação de Dabs contínua (Sem 'gaps' ou buracos) ─────────────
    def test_06_dab_interpolation_continuity(self):
        """Valida que um traço diagonal rápido interpola dabs sem deixar buracos vazios."""
        self.facade.set_engine_type(int(aen.EngineType.Inker))
        profile = self.facade.get_brush_profile()
        profile.brush_size = 14.0
        profile.spacing_factor = 0.1  # 10% spacing bem denso
        profile.opacity = 1.0
        profile.base_color = aen.ColorRGBA(0, 0, 255, 255)

        # Traço rápido com passos interpolados
        self._draw_line(20, 20, 180, 180, steps=30, pressure=1.0)

        arr = self._get_canvas_array()
        # Amostra vários pontos ao longo da diagonal principal (x, x)
        for d in range(30, 170, 10):
            px = arr[d, d]
            self.assertGreater(px[3], 200, f"Ponto diagonal ({d}, {d}) deve estar preenchido, alpha={px[3]}")
            self.assertGreaterEqual(int(px[2]), 250, f"Canal azul no ponto ({d}, {d}) deve ser >= 250, obtido {px[2]}")

    # ── 7. PencilEngine: Modulação de Grão e Rugosidade de Grafite ───────────
    def test_07_pencil_grain_texture_modulation(self):
        """Valida que ativar brush_grain_enabled modula fisicamente a deposição estocástica do grafite."""
        from ui.engine_backends.aladyn import AladynBackend

        backend = AladynBackend()
        backend.set_active_document_context("test_doc_pencil", 200, 200)
        backend.set_engine_type(1)  # Pencil
        backend.set_brush_size(24.0)
        backend.set_brush_opacity(0.85)
        backend.set_brush_color(0.0, 0.0, 0.0)

        # 1. Desenha sem textura
        backend.set_brush_grain_enabled(False)
        backend.begin_stroke_raw(50.0, 50.0, 0.6)
        backend.end_stroke_raw()
        buf_no_grain = backend.get_pixel_buffer()
        arr_no_grain = np.frombuffer(buf_no_grain, dtype=np.uint8).reshape((200, 200, 4))
        drawn_no_grain = np.count_nonzero(arr_no_grain[:, :, 0] < 250)

        # 2. Limpa e desenha com textura de ruído ativa
        backend.clear_canvas()
        backend.set_brush_grain_enabled(True)
        backend.set_brush_height_preset(3)  # NoiseGrain
        backend.set_brush_grain_contrast(1.5)
        backend.begin_stroke_raw(50.0, 50.0, 0.6)
        backend.end_stroke_raw()
        buf_grain = backend.get_pixel_buffer()
        arr_grain = np.frombuffer(buf_grain, dtype=np.uint8).reshape((200, 200, 4))
        drawn_grain = np.count_nonzero(arr_grain[:, :, 0] < 250)

        # Com grão ativo, a textura porosa produz dabs fraturados com menos pixels contíguos
        self.assertGreater(drawn_no_grain, 0, "Traço sem grão deve desenhar")
        self.assertGreater(drawn_grain, 0, "Traço com grão deve desenhar")
        self.assertNotEqual(drawn_no_grain, drawn_grain, "Traço com grão deve ter deposição estocástica diferente do traço liso")

    # ── 8. Propagação de Presets de Lápis via apply_brush_preset_dict ─────────
    def test_08_brush_preset_propagation_through_backend(self):
        """Valida que presets curados de Lápis e Carvão ativam corretamente os grãos na ponte."""
        from ui.engine_backends.aladyn import AladynBackend

        backend = AladynBackend()
        backend.set_active_document_context("test_doc_preset", 200, 200)

        pencil_preset = {
            "engine_type": 1,
            "brush_size": 8.0,
            "opacity": 0.90,
            "spacing_factor": 0.06,
            "hardness": 0.6,
            "pencil_graphite_hardness": 0.1,
            "brush_grain_enabled": True,
            "brush_height_preset": 0,
            "brush_grain_contrast": 1.0,
            "brush_grain_scale": 1.0,
        }

        backend.apply_brush_preset_dict(pencil_preset)
        prof_dict = backend.get_brush_profile_dict()

        self.assertTrue(prof_dict.get("brush_grain_enabled", False), "brush_grain_enabled deve estar True após aplicar preset")
        self.assertEqual(backend.get_active_engine_type(), 1, "Engine type deve ser 1 (Pencil)")
        self.assertAlmostEqual(prof_dict.get("pencil_graphite_hardness", 0.0), 0.1)


if __name__ == "__main__":
    unittest.main()
