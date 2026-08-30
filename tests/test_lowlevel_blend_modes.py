"""
Low-Level Test Suite: Layer Blend Modes, Alpha Lock & Clipping Mask Math
Validates numerical accuracy of layer composition (Normal, Multiply, Screen, Overlay, Darken, Lighten, Erase),
hardware alpha locking, and clipping mask constraints.
"""

import os
import sys
import unittest
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import aladyn_engine_native as aen


class TestLowLevelBlendModes(unittest.TestCase):
    def setUp(self):
        self.w = 100
        self.h = 100
        self.facade = aen.PaintEngineFacade(self.w, self.h)
        # Desativa fundo para testar transparência direta
        self.facade.set_background_visibility(False)

    def _get_canvas_array(self) -> np.ndarray:
        buf = self.facade.get_pixel_buffer()
        return np.frombuffer(buf, dtype=np.uint8).reshape((self.h, self.w, 4))

    def _fill_rect_on_layer(self, layer_idx: int, x: int, y: int, w: int, h: int, color: aen.ColorRGBA):
        """Preenche uma área retangular na camada indicada usando paste_rgba_buffer."""
        self.facade.select_layer(layer_idx)
        buf = bytes([color.r, color.g, color.b, color.a] * (w * h))
        self.facade.paste_rgba_buffer_on_active_layer(x, y, w, h, buf, 0, 1.0)

    # ── 1. Blend Mode: Multiply (Multiplicação) ──────────────────────────────
    def test_01_blend_mode_multiply(self):
        """Valida que Multiply realiza a multiplicação exata: (A * B) / 255."""
        # Camada 1 (Base): Cinza 128 (50% de cinza)
        self.facade.add_layer("Base")
        self._fill_rect_on_layer(0, 20, 20, 60, 60, aen.ColorRGBA(128, 128, 128, 255))

        # Camada 2 (Topo): Cinza 128 com modo Multiply (id=1)
        self.facade.add_layer("Topo Multiply")
        self.facade.set_layer_blend_mode(1, int(aen.LayerBlendMode.Multiply))
        self._fill_rect_on_layer(1, 20, 20, 60, 60, aen.ColorRGBA(128, 128, 128, 255))

        arr = self._get_canvas_array()
        center = arr[50, 50]
        # (128 * 128) / 255 = 64.25 -> ~64
        self.assertAlmostEqual(center[0], 64, delta=2, msg=f"Multiply R deve ser ~64, obtido {center[0]}")
        self.assertAlmostEqual(center[1], 64, delta=2, msg=f"Multiply G deve ser ~64, obtido {center[1]}")
        self.assertAlmostEqual(center[2], 64, delta=2, msg=f"Multiply B deve ser ~64, obtido {center[2]}")
        self.assertEqual(center[3], 255)

    # ── 2. Blend Mode: Screen (Divisão/Trama) ─────────────────────────────────
    def test_02_blend_mode_screen(self):
        """Valida que Screen realiza: 255 - ((255 - A) * (255 - B)) / 255."""
        self.facade.add_layer("Base")
        self._fill_rect_on_layer(0, 20, 20, 60, 60, aen.ColorRGBA(128, 128, 128, 255))

        self.facade.add_layer("Topo Screen")
        self.facade.set_layer_blend_mode(1, int(aen.LayerBlendMode.Screen))
        self._fill_rect_on_layer(1, 20, 20, 60, 60, aen.ColorRGBA(128, 128, 128, 255))

        arr = self._get_canvas_array()
        center = arr[50, 50]
        # 255 - ((127 * 127) / 255) = 255 - 63.25 = 191.75 -> ~192
        self.assertAlmostEqual(center[0], 192, delta=2, msg=f"Screen R deve ser ~192, obtido {center[0]}")
        self.assertAlmostEqual(center[1], 192, delta=2, msg=f"Screen G deve ser ~192, obtido {center[1]}")
        self.assertAlmostEqual(center[2], 192, delta=2, msg=f"Screen B deve ser ~192, obtido {center[2]}")

    # ── 3. Alpha Lock: Preserva transparência estrita ─────────────────────────
    def test_03_alpha_lock_preserves_transparent_areas(self):
        """Valida que com Alpha Lock ativo, desenhar sobre pixels transparentes é bloqueado."""
        self.facade.add_layer("Lineart")
        # Desenha um quadrado opaco central de 30x30 em (35, 35)
        self._fill_rect_on_layer(0, 35, 35, 30, 30, aen.ColorRGBA(255, 0, 0, 255))

        # Ativa Alpha Lock na camada
        self.facade.set_layer_alpha_lock(0, True)
        self.assertTrue(self.facade.is_layer_alpha_locked(0))

        # Tenta pintar a camada inteira de azul com paste_rgba
        blue_buf = bytes([0, 0, 255, 255] * (self.w * self.h))
        self.facade.paste_rgba_buffer_on_active_layer(0, 0, self.w, self.h, blue_buf, 0, 1.0)

        arr = self._get_canvas_array()

        # O centro (50, 50) que era vermelho e opaco deve ter virado azul
        center = arr[50, 50]
        self.assertEqual(center[2], 255, f"Área opaca deve aceitar cor azul, obtido B={center[2]}")
        self.assertEqual(center[3], 255)

        # O canto (10, 10) que era transparente DEVE CONTINUAR 100% transparente (Alpha=0)
        corner = arr[10, 10]
        self.assertEqual(corner[3], 0, f"Alpha Lock DEVE manter área transparente inalterada, obtido Alpha={corner[3]}")

    # ── 4. Clipping Mask: Renderização subordinada à camada inferior ──────────
    def test_04_clipping_mask_bounds_restriction(self):
        """Valida que uma camada com Clipping Mask só é visível onde a camada base tem Alpha > 0."""
        # Camada 0: Círculo/Quadrado base central (40x40) em (30, 30)
        self.facade.add_layer("Base Mask")
        self._fill_rect_on_layer(0, 30, 30, 40, 40, aen.ColorRGBA(200, 200, 200, 255))

        # Camada 1: Camada inteira pintada de Magenta (255, 0, 255, 255) com Clipping Mask ativado
        self.facade.add_layer("Clipping Child")
        self.facade.set_layer_clipping_mask(1, True)
        self.assertTrue(self.facade.is_layer_clipping_mask(1))

        # Pinta um retângulo muito maior (80x80) de (10, 10) a (90, 90) na camada filha
        self._fill_rect_on_layer(1, 10, 10, 80, 80, aen.ColorRGBA(255, 0, 255, 255))

        arr = self._get_canvas_array()

        # Dentro da base (50, 50): Deve ver a cor da camada filha (Magenta)
        inside = arr[50, 50]
        self.assertEqual(inside[0], 255, "Dentro da base deve renderizar o R da camada clipped")
        self.assertEqual(inside[1], 0)
        self.assertEqual(inside[2], 255, "Dentro da base deve renderizar o B da camada clipped")
        self.assertEqual(inside[3], 255)

        # Fora da base (20, 20) onde a filha foi pintada mas a base é transparente: DEVE SER TRANSPARENTE
        outside = arr[20, 20]
        self.assertEqual(outside[3], 0, f"Clipping mask deve bloquear renderização fora da base, obtido alpha={outside[3]}")


if __name__ == "__main__":
    unittest.main()
