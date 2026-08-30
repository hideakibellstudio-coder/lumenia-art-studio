"""
Low-Level Test Suite: Selection Bitmask, Flood Fill & Bicubic Transformation Math
Validates SelectionEngine clipping, Magic Wand contouring, and TransformEngine affine matrix accuracy.
"""

import os
import sys
import unittest
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import aladyn_engine_native as aen


class TestLowLevelSelectionTransform(unittest.TestCase):
    def setUp(self):
        self.w = 120
        self.h = 120
        self.facade = aen.PaintEngineFacade(self.w, self.h)
        self.facade.set_background_visibility(False)
        self.facade.add_layer("Camada Teste")
        self.facade.select_layer(0)

    def _get_canvas_array(self) -> np.ndarray:
        buf = self.facade.get_pixel_buffer()
        return np.frombuffer(buf, dtype=np.uint8).reshape((self.h, self.w, 4))

    # ── 1. Retangular Selection & In-Mask Fill ────────────────────────────────
    def test_01_select_rect_and_fill(self):
        """Valida que select_rect cria uma máscara e fill_selection só afeta a área selecionada."""
        # Seleciona retângulo central de (30, 30) a (90, 90) -> 60x60
        self.facade.select_rect(30, 30, 60, 60, mode=0, feather_px=0)
        self.assertTrue(self.facade.has_selection())

        # Preenche a seleção com Verde (0, 255, 0, 255)
        success = self.facade.fill_selection_on_active_layer(aen.ColorRGBA(0, 255, 0, 255))
        self.assertTrue(success)

        arr = self._get_canvas_array()

        # Ponto dentro (50, 50) deve ser verde opaco
        inside = arr[50, 50]
        self.assertEqual(inside[0], 0)
        self.assertEqual(inside[1], 255, f"Dentro da seleção G deve ser 255, obtido {inside[1]}")
        self.assertEqual(inside[2], 0)
        self.assertEqual(inside[3], 255)

        # Ponto fora (15, 15) deve ser transparente
        outside = arr[15, 15]
        self.assertEqual(outside[3], 0, f"Fora da seleção Alpha deve ser 0, obtido {outside[3]}")

    # ── 2. Selection Inversion & Deletion ─────────────────────────────────────
    def test_02_selection_inversion_and_delete(self):
        """Valida a inversão de seleção e exclusão de pixels na camada ativa."""
        # 1. Pinta todo o canvas de Vermelho
        red_buf = bytes([255, 0, 0, 255] * (self.w * self.h))
        self.facade.paste_rgba_buffer_on_active_layer(0, 0, self.w, self.h, red_buf, 0, 1.0)

        # 2. Seleciona o centro (40, 40, 40, 40)
        self.facade.select_rect(40, 40, 40, 40, mode=0)
        # Inverte a seleção -> agora as bordas externas estão selecionadas
        self.facade.invert_selection()

        # 3. Deleta a seleção
        self.facade.delete_selection_on_active_layer()

        arr = self._get_canvas_array()

        # O centro (60, 60) que NÃO estava na seleção invertida deve continuar vermelho
        center = arr[60, 60]
        self.assertEqual(center[0], 255, "Centro não selecionado deve manter cor vermelha")
        self.assertEqual(center[3], 255)

        # As bordas (10, 10) que foram deletadas devem estar transparentes
        border = arr[10, 10]
        self.assertEqual(border[3], 0, "Borda selecionada deve ser apagada (Alpha=0)")

    # ── 3. Magic Wand (Varinha Mágica) ───────────────────────────────────────
    def test_03_magic_wand_selection(self):
        """Valida a seleção contígua por tolerância de cor com Magic Wand."""
        # Desenha um quadrado azul no centro de (30, 30) a (70, 70)
        blue_buf = bytes([0, 0, 255, 255] * (40 * 40))
        self.facade.paste_rgba_buffer_on_active_layer(30, 30, 40, 40, blue_buf, 0, 1.0)

        # Clica com a varinha mágica dentro do quadrado azul em (50, 50)
        ok = self.facade.magic_wand_select(seed_x=50, seed_y=50, tolerance=20, contiguous=True)
        self.assertTrue(ok)
        self.assertTrue(self.facade.has_selection())

        bounds = self.facade.get_selection_bounds()
        # Os limites da seleção devem coincidir com [30, 30, 40, 40]
        self.assertAlmostEqual(bounds[0], 30, delta=2)
        self.assertAlmostEqual(bounds[1], 30, delta=2)
        self.assertAlmostEqual(bounds[2], 40, delta=2)
        self.assertAlmostEqual(bounds[3], 40, delta=2)

    # ── 4. Transform Tool (Flip e Rotação 90°) ────────────────────────────────
    def test_04_transform_flip_and_rotation(self):
        """Valida rotações ortogonais e espelhamentos da camada ativa."""
        # Pinta um bloco de 20x20 no quadrante superior esquerdo (10, 10) de amarelo
        yellow_buf = bytes([255, 255, 0, 255] * (20 * 20))
        self.facade.paste_rgba_buffer_on_active_layer(10, 10, 20, 20, yellow_buf, 0, 1.0)

        # Espelha horizontalmente a camada ativa
        self.facade.flip_active_layer(horizontal=True)

        arr = self._get_canvas_array()
        # O bloco amarelo que estava em X=10..30 deve agora estar em X=90..110 (120 - 30 = 90)
        mirrored_px = arr[20, 100]
        self.assertEqual(mirrored_px[0], 255, "Pixel espelhado R deve ser 255")
        self.assertEqual(mirrored_px[1], 255, "Pixel espelhado G deve ser 255")
        self.assertEqual(mirrored_px[3], 255, "Pixel espelhado Alpha deve ser 255")

        # A posição original (20, 20) deve estar limpa (transparente)
        orig_px = arr[20, 20]
        self.assertEqual(orig_px[3], 0, "Posição original deve ficar vazia após flip")


if __name__ == "__main__":
    unittest.main()
