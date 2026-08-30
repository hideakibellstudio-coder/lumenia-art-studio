"""
Low-Level Test Suite: Tile Boundary Crossing, Multi-Step Undo/Redo & Memory Stress
Validates dirty tile tracking across 64x64 boundaries, undo snapshot accuracy, and memory limits.
"""

import os
import sys
import unittest
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import aladyn_engine_native as aen


class TestLowLevelUndoTileStress(unittest.TestCase):
    def setUp(self):
        # Canvas de 256x256 abrangendo exatamente 4x4 tiles de 64x64
        self.w = 256
        self.h = 256
        self.facade = aen.PaintEngineFacade(self.w, self.h)
        self.facade.set_background_visibility(False)
        self.facade.add_layer("Camada Estresse")
        self.facade.select_layer(0)

    def _get_canvas_array(self) -> np.ndarray:
        buf = self.facade.get_pixel_buffer()
        return np.frombuffer(buf, dtype=np.uint8).reshape((self.h, self.w, 4))

    def _draw_stroke(self, x0, y0, x1, y1, color: aen.ColorRGBA, size=15.0):
        profile = self.facade.get_brush_profile()
        profile.engine_type = aen.EngineType.Inker
        profile.brush_size = size
        profile.opacity = 1.0
        profile.base_color = color
        self.facade.set_engine_type(int(aen.EngineType.Inker))

        self.facade.begin_stroke_raw(float(x0), float(y0), 1.0)
        self.facade.update_stroke_raw(float(x1), float(y1), 1.0)
        self.facade.end_stroke_raw()

    # ── 1. Tile Boundary Crossing ($64\times64$) ──────────────────────────────
    def test_01_tile_boundary_crossing(self):
        """Valida traço longo cruzando as fronteiras de 4 tiles distintos (0,0)->(1,1)->(2,2)->(3,3)."""
        # Traço de (10, 10) até (240, 240)
        self._draw_stroke(10, 10, 240, 240, aen.ColorRGBA(255, 100, 0, 255), size=12.0)

        arr = self._get_canvas_array()

        # Amostra um ponto em cada um dos 4 tiles cruzados:
        # Tile (0,0): px (30, 30)
        # Tile (1,1): px (90, 90)
        # Tile (2,2): px (150, 150)
        # Tile (3,3): px (210, 210)
        for pt in (30, 90, 150, 210):
            px = arr[pt, pt]
            self.assertGreater(px[3], 200, f"Tile cruzado em ({pt}, {pt}) deve ter pixels gravados, obtido alpha={px[3]}")
            self.assertEqual(px[0], 255, f"Canal R em ({pt}, {pt}) deve ser 255")

    # ── 2. Multi-Step Undo / Redo Determinism ─────────────────────────────────
    def test_02_multistep_undo_redo_fidelity(self):
        """Valida que 3 traços em posições distintas podem ser desfeitos e refeitos perfeitamente."""
        # Traço 1: Vermelho no topo (50, 50)
        self._draw_stroke(40, 50, 60, 50, aen.ColorRGBA(255, 0, 0, 255), size=20.0)
        arr_step1 = self._get_canvas_array().copy()

        # Traço 2: Verde no meio (128, 128)
        self._draw_stroke(118, 128, 138, 128, aen.ColorRGBA(0, 255, 0, 255), size=20.0)
        arr_step2 = self._get_canvas_array().copy()

        # Traço 3: Azul na base (200, 200)
        self._draw_stroke(190, 200, 210, 200, aen.ColorRGBA(0, 0, 255, 255), size=20.0)
        arr_step3 = self._get_canvas_array().copy()

        # Verifica estado atual (todos os 3 traços visíveis)
        self.assertGreater(arr_step3[50, 50, 3], 200)
        self.assertGreater(arr_step3[128, 128, 3], 200)
        self.assertGreater(arr_step3[200, 200, 3], 200)

        # 1x UNDO -> Remove traço 3 (Azul)
        self.assertTrue(self.facade.undo())
        arr_after_undo1 = self._get_canvas_array()
        self.assertEqual(arr_after_undo1[200, 200, 3], 0, "Traço 3 deve ter sido desfeito")
        self.assertGreater(arr_after_undo1[128, 128, 3], 200, "Traço 2 deve permanecer")

        # 2x UNDO -> Remove traço 2 (Verde)
        self.assertTrue(self.facade.undo())
        arr_after_undo2 = self._get_canvas_array()
        self.assertEqual(arr_after_undo2[128, 128, 3], 0, "Traço 2 deve ter sido desfeito")
        self.assertGreater(arr_after_undo2[50, 50, 3], 200, "Traço 1 deve permanecer")

        # 1x REDO -> Restaura traço 2 (Verde)
        self.assertTrue(self.facade.redo())
        arr_after_redo1 = self._get_canvas_array()
        self.assertGreater(arr_after_redo1[128, 128, 3], 200, "Traço 2 deve ser restaurado")
        self.assertEqual(arr_after_redo1[200, 200, 3], 0, "Traço 3 ainda não deve existir")

    # ── 3. Redo Invalidation on New Stroke ───────────────────────────────────
    def test_03_redo_invalidation_on_new_stroke(self):
        """Valida que desenhar um novo traço após um undo invalida e descarta a pilha de redo."""
        # Traço 1
        self._draw_stroke(30, 30, 50, 30, aen.ColorRGBA(255, 0, 0, 255))
        # Traço 2
        self._draw_stroke(100, 100, 120, 100, aen.ColorRGBA(0, 255, 0, 255))

        # Undo do traço 2
        self.facade.undo()

        # Novo Traço 3 diferente
        self._draw_stroke(180, 180, 200, 180, aen.ColorRGBA(0, 0, 255, 255))

        # Redo NÃO deve ser mais possível
        can_redo = self.facade.redo()
        self.assertFalse(can_redo, "Redo deve retornar False após novo traço invalidar a pilha")

    # ── 4. Undo Step / Memory Limits ─────────────────────────────────────────
    def test_04_undo_limit_pruning(self):
        """Valida que configurar limite estrito de passos de undo descarta os passos mais antigos sem crash."""
        self.facade.set_undo_max_steps(3)
        self.assertEqual(self.facade.get_undo_max_steps(), 3)

        # Executa 5 traços consecutivos
        for i in range(5):
            self._draw_stroke(20 + i * 40, 50, 40 + i * 40, 50, aen.ColorRGBA(i * 40, 255 - i * 40, 128, 255))

        # Deve conseguir dar no máximo 3 undos (devido ao limite de 3 passos)
        undo_count = 0
        while self.facade.undo():
            undo_count += 1

        self.assertEqual(undo_count, 3, f"Deve permitir exatamente 3 undos conforme o limite max_steps, obtido {undo_count}")


if __name__ == "__main__":
    unittest.main()
