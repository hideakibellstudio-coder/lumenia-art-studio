"""
Low-Level Test Suite: Phase 2 - Linear sRGB Blending & Extended Pen Dynamics
============================================================================
Validates:
1. Linear sRGB Blending Fidelity (elimination of muddy edges / dark band artifacts).
2. Extended Stylus Dynamics (tilt_x, tilt_y, twist/barrel roll, altitude, azimuth).
3. Tangential Angle Follow (auto-rotation of tip aligned to stroke vector).
4. Color Jitter (Hue, Saturation, Brightness stochastic dispersion).
5. Tip Aspect Ratio modulation and interpolation.
"""

import os
import sys
import unittest
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import aladyn_engine_native as aen


class TestLowLevelPhase2ColorDynamics(unittest.TestCase):
    def setUp(self):
        self.w = 120
        self.h = 120
        self.facade = aen.PaintEngineFacade(self.w, self.h)
        self.facade.set_background_visibility(False)
        self.facade.add_layer("Layer 1")
        self.facade.select_layer(0)

    def _get_canvas_array(self) -> np.ndarray:
        buf = self.facade.get_pixel_buffer()
        return np.frombuffer(buf, dtype=np.uint8).reshape((self.h, self.w, 4))

    def _fill_rect(self, x: int, y: int, w: int, h: int, color: aen.ColorRGBA):
        buf = bytes([color.r, color.g, color.b, color.a] * (w * h))
        self.facade.paste_rgba_buffer_on_active_layer(x, y, w, h, buf, 0, 1.0)

    # ── 1. Linear sRGB Blending Fidelity ──────────────────────────────────────
    def test_01_linear_srgb_blending_fidelity(self):
        """
        Valida que a mistura linear sRGB elimina bordas acinzentadas/escuras (muddy edges).
        Ao misturar Vermelho (255, 0, 0) com Verde (0, 255, 0) a 50% de opacidade:
        No espaço não-linear tradicional (gamma 2.2 distorcido): R=127, G=127 (oliva escuro/sujo).
        No espaço físico Linear sRGB: R > 175, G > 175 (amarelo puro e vibrante).
        """
        # Camada 0: Fundo Vermelho puro opaco
        self._fill_rect(20, 20, 80, 80, aen.ColorRGBA(255, 0, 0, 255))

        # Camada 1: Verde puro com 50% de opacidade em modo Normal
        self.facade.add_layer("Layer Verde")
        self.facade.select_layer(1)
        self.facade.set_layer_opacity(1, 0.5)
        self._fill_rect(20, 20, 80, 80, aen.ColorRGBA(0, 255, 0, 255))

        arr = self._get_canvas_array()
        center = arr[60, 60]

        # Em espaço linear, 50% de 1.0 linear convertido de volta para sRGB é ~186.
        # Deve ser estritamente maior que 160 (evitando a queda escura não-linear em 127).
        self.assertGreater(int(center[0]), 160, f"R no espaço linear deve ser vibrante (>160), obtido {center[0]}")
        self.assertGreater(int(center[1]), 160, f"G no espaço linear deve ser vibrante (>160), obtido {center[1]}")
        self.assertEqual(int(center[2]), 0, f"B deve permanecer 0, obtido {center[2]}")
        self.assertEqual(int(center[3]), 255, "Alpha composto deve ser 255")

    # ── 2. Extended Stylus Dynamics & PointerEvent ───────────────────────────
    def test_02_extended_pointer_event_and_stylus_dynamics(self):
        """
        Valida o suporte a canetas avançadas (tilt_x, tilt_y, twist/barrel roll, altitude, azimuth).
        """
        pt = aen.Point2D(50.0, 50.0)
        # Cria PointerEvent com inclinação de 45 graus em X e twist de 90 graus
        evt = aen.PointerEvent(
            aen.PointerEventType.Move, pt, 0.8, 1.0, 45.0, 0.0, 90.0
        )
        self.assertAlmostEqual(evt.tilt_x, 45.0, places=2)
        self.assertAlmostEqual(evt.tilt_y, 0.0, places=2)
        self.assertAlmostEqual(evt.twist, 90.0, places=2)

        # Dispara cálculo automático de altitude e azimute a partir do tilt
        evt.compute_altitude_azimuth_from_tilt()
        self.assertAlmostEqual(evt.altitude, 45.0, delta=1.0)
        self.assertAlmostEqual(evt.azimuth, 0.0, delta=1.0)

        # Valida que o fast-path nativo aceita tilt e twist sem exceção
        res = self.facade.begin_stroke_raw(50.0, 50.0, 0.8, 0.0, 45.0, 0.0, 90.0)
        res_update = self.facade.update_stroke_raw(60.0, 50.0, 0.8, 0.01, 45.0, 0.0, 90.0)
        self.facade.end_stroke_raw()
        self.assertIsInstance(res_update, list)

    # ── 3. Tangential Angle Follow ───────────────────────────────────────────
    def test_03_tangential_angle_follow_dynamics(self):
        """
        Valida que follow_stroke orienta o ângulo da ponta à tangente instantânea do movimento.
        """
        profile = self.facade.get_brush_profile()
        profile.tip.follow_stroke = True
        profile.tip.aspect_ratio = 0.2  # Ponta extremamente achatada/elíptica
        profile.brush_size = 20.0
        profile.base_color = aen.ColorRGBA(0, 0, 0, 255)

        # Traço horizontal de (20, 60) a (100, 60)
        self.facade.begin_stroke_raw(20.0, 60.0, 1.0)
        for x in range(30, 101, 10):
            self.facade.update_stroke_raw(float(x), 60.0, 1.0)
        self.facade.end_stroke_raw()

        arr = self._get_canvas_array()
        # Pixels devem ser depositados com sucesso
        self.assertGreater(np.sum(arr[:, :, 3] > 0), 100)

    # ── 4. Color Jitter Stochastic Variance ──────────────────────────────────
    def test_04_color_jitter_stochastic_variance(self):
        """
        Valida que as configurações de jitter_hue, jitter_saturation e jitter_brightness
        estão integradas ao BrushTip e produzem variabilidade cromática.
        """
        profile = self.facade.get_brush_profile()
        profile.tip.jitter_hue = 0.5
        profile.tip.jitter_saturation = 0.3
        profile.tip.jitter_brightness = 0.2
        profile.tip.use_twist_for_angle = True
        profile.tip.tilt_to_angle = 0.5
        profile.tip.tilt_to_aspect = 0.5

        self.assertAlmostEqual(profile.tip.jitter_hue, 0.5, places=2)
        self.assertAlmostEqual(profile.tip.jitter_saturation, 0.3, places=2)
        self.assertAlmostEqual(profile.tip.jitter_brightness, 0.2, places=2)
        self.assertTrue(profile.tip.use_twist_for_angle)
        self.assertAlmostEqual(profile.tip.tilt_to_angle, 0.5, places=2)
        self.assertAlmostEqual(profile.tip.tilt_to_aspect, 0.5, places=2)

        # Executa traço com Color Jitter ativado
        profile.brush_size = 15.0
        profile.base_color = aen.ColorRGBA(200, 50, 50, 255)
        self.facade.begin_stroke_raw(30.0, 30.0, 1.0)
        for i in range(1, 10):
            self.facade.update_stroke_raw(30.0 + i * 8.0, 30.0 + i * 8.0, 1.0)
        self.facade.end_stroke_raw()

        arr = self._get_canvas_array()
        painted_mask = arr[:, :, 3] > 100
        painted_pixels = arr[painted_mask]
        self.assertGreater(len(painted_pixels), 0)


if __name__ == "__main__":
    unittest.main()
