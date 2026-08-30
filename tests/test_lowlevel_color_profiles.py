"""
Low-Level Test Suite: Color Profiles, Display Buffer & Daltonism Proofing Math
Validates C++ ColorProfile matrix calculations, display pixel buffers, and soft-proofing.
"""

import os
import sys
import unittest
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import aladyn_engine_native as aen


class TestLowLevelColorProfiles(unittest.TestCase):
    def setUp(self):
        self.w = 50
        self.h = 50
        self.facade = aen.PaintEngineFacade(self.w, self.h)
        self.facade.set_background_visibility(False)
        self.facade.add_layer("Camada Cor")
        self.facade.select_layer(0)

    # ── 1. Color Profile ID Setting and Querying ─────────────────────────────
    def test_01_profile_id_roundtrip(self):
        """Valida que todos os 14 IDs de perfis de cores podem ser ativados e consultados."""
        # 0: sRGB, 1: Display P3, 2: Adobe RGB, 4: SWOP, 8: Protanopia, 12: Linear sRGB, 13: ACEScg
        for profile_id in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
            self.facade.set_color_profile(profile_id)
            self.assertEqual(self.facade.get_color_profile(), profile_id)

    # ── 2. Display Pixel Buffer Generation ───────────────────────────────────
    def test_02_display_pixel_buffer_matches_canvas_size(self):
        """Valida se o display pixel buffer possui exatamente W * H * 4 bytes e não é nulo."""
        self.facade.set_color_profile(0)  # sRGB
        # Pinta um quadrado vermelho de 20x20
        red_buf = bytes([255, 0, 0, 255] * (20 * 20))
        self.facade.paste_rgba_buffer_on_active_layer(10, 10, 20, 20, red_buf, 0, 1.0)

        disp_buf = self.facade.get_display_pixel_buffer()
        self.assertIsNotNone(disp_buf)
        self.assertEqual(len(disp_buf), self.w * self.h * 4)

        arr = np.frombuffer(disp_buf, dtype=np.uint8).reshape((self.h, self.w, 4))
        # Ponto (20, 20) deve ser vermelho
        px = arr[20, 20]
        self.assertEqual(px[0], 255)
        self.assertEqual(px[3], 255)

    # ── 3. Protanopia (Daltonismo) Soft-Proofing ─────────────────────────────
    def test_03_protanopia_simulation_reduces_red(self):
        """Valida que no modo de prova Protanopia (id=8), pixels puramente vermelhos sofrem transformação espectral."""
        # Pinta um quadrado vermelho puro (255, 0, 0, 255)
        red_buf = bytes([255, 0, 0, 255] * (20 * 20))
        self.facade.paste_rgba_buffer_on_active_layer(10, 10, 20, 20, red_buf, 0, 1.0)

        # 1. Pega no modo sRGB normal
        self.facade.set_color_profile(0)
        disp_srgb = np.frombuffer(self.facade.get_display_pixel_buffer(), dtype=np.uint8).reshape((self.h, self.w, 4))
        px_srgb = disp_srgb[20, 20]
        self.assertEqual(px_srgb[0], 255, "sRGB normal deve ter R=255")

        # 2. Ativa prova de Protanopia (id=8)
        self.facade.set_color_profile(8)
        disp_prot = np.frombuffer(self.facade.get_display_pixel_buffer(), dtype=np.uint8).reshape((self.h, self.w, 4))
        px_prot = disp_prot[20, 20]

        # Em protanopia, vermelho puro perde a saturação avermelhada e converte-se em tom ocre/amarelado/cinza
        # Logo, R diminui ou G aumenta
        self.assertNotEqual(tuple(px_srgb), tuple(px_prot), "A prova de Protanopia DEVE transformar os valores RGB de exibição")


if __name__ == "__main__":
    unittest.main()
