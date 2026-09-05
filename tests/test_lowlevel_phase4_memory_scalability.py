"""
Low-Level Test Suite: Phase 4 - Format & Memory Scalability (Heavy-Duty Canvas / 600 DPI)
Validates:
1. LZ4 Streaming Compression of Inactive Tiles (lossless roundtrip & RAM reduction)
2. Copy-On-Write (COW) Layer Duplication (O(1) allocation & buffer unsharing on write)
3. Transparent Inactive Layer Decompression during Compositing
4. Undo Scratch Disk Paging and Safe History Restoration
"""

import os
import sys
import unittest
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import aladyn_engine_native as aen


class TestPhase4MemoryScalability(unittest.TestCase):
    def setUp(self):
        self.w = 256
        self.h = 256
        self.facade = aen.PaintEngineFacade(self.w, self.h)
        self.facade.set_background_visibility(False)

    def _get_canvas_array(self) -> np.ndarray:
        buf = self.facade.get_pixel_buffer()
        return np.frombuffer(buf, dtype=np.uint8).reshape((self.h, self.w, 4))

    def _draw_stroke(self, x0, y0, x1, y1, color: aen.ColorRGBA, size=20.0, steps=20):
        profile = self.facade.get_brush_profile()
        profile.engine_type = aen.EngineType.Inker
        profile.brush_size = size
        profile.opacity = 1.0
        profile.base_color = color
        self.facade.set_engine_type(int(aen.EngineType.Inker))

        self.facade.begin_stroke_raw(float(x0), float(y0), 1.0)
        for i in range(1, steps + 1):
            t = i / float(steps)
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            self.facade.update_stroke_raw(x, y, 1.0)
        self.facade.end_stroke_raw()

    # ── 1. LZ4 Compression Roundtrip & RAM Savings ────────────────────────────
    def test_01_lz4_tile_compression_roundtrip(self):
        """Valida que a compressao LZ4 de tiles reduz a memoria e descomprime com 100% de fidelidade."""
        self.facade.select_layer(0)

        # Desenha formas com cores solidas para criar tiles com conteudo
        self._draw_stroke(20, 20, 220, 220, aen.ColorRGBA(200, 50, 80, 255), size=30.0)

        # Captura pixels antes da compressao
        pixels_before = self._get_canvas_array().copy()

        # Cria uma segunda camada e a torna ativa, deixando a primeira inativa
        self.facade.add_layer("Layer 2")
        self.facade.select_layer(1)

        mem_uncompressed = self.facade.get_total_tile_memory_mb()
        self.assertGreater(mem_uncompressed, 0.0)

        # Comprime camadas inativas
        compressed_count = self.facade.compress_inactive_layers()
        self.assertGreater(compressed_count, 0, "Deveria ter comprimido ao menos um tile da Layer 1")

        mem_compressed = self.facade.get_total_tile_memory_mb()
        self.assertLess(mem_compressed, mem_uncompressed, "Memoria total com tiles LZ4 comprimidos deve ser menor")

        # Descomprime explicitamente todas as camadas
        decompressed_count = self.facade.decompress_all_layers()
        self.assertGreaterEqual(decompressed_count, compressed_count)

        # Oculta layer 2 temporariamente para verificar Layer 1
        self.facade.set_layer_visibility(1, False)
        pixels_after = self._get_canvas_array()
        np.testing.assert_array_equal(
            pixels_before,
            pixels_after,
            err_msg="Lossless check: pixels descomprimidos via LZ4 devem ser identicos bit a bit"
        )

    # ── 2. Copy-on-Write (COW) Layer Duplication ──────────────────────────────
    def test_02_copy_on_write_layer_duplication(self):
        """Valida duplicacao de camada via COW: ponteiros compartilhados em O(1) e copia sob demanda na escrita."""
        self.assertEqual(self.facade.get_drawing_layer_count(), 1)
        self.facade.select_layer(0)
        self._draw_stroke(50, 50, 200, 50, aen.ColorRGBA(0, 200, 100, 255), size=25.0)

        cow_shared_before = self.facade.get_cow_shared_tiles_count()
        self.assertEqual(cow_shared_before, 0, "Sem duplicacao, nao ha tiles compartilhados")

        # Duplica a camada 0
        self.facade.duplicate_layer(0)
        self.assertEqual(self.facade.get_drawing_layer_count(), 2)

        # Agora tiles devem ser compartilhados (use_count > 1) sem duplicar buffers em RAM
        cow_shared_after = self.facade.get_cow_shared_tiles_count()
        self.assertGreater(cow_shared_after, 0, "Tiles da camada duplicada devem ser compartilhados via COW")

        # Desenha na camada duplicada (layer 1)
        self.facade.select_layer(1)
        self._draw_stroke(50, 150, 200, 150, aen.ColorRGBA(255, 0, 0, 255), size=25.0)

        # O tile modificado em (50..200, 150) teve ensureUnique() executado.
        # Verifica que a camada base (layer 0) permanece intocada na regiao (50..200, 150)
        self.facade.set_layer_visibility(1, False) # Oculta duplicada para inspecionar base
        base_pixels = self._get_canvas_array()
        # Pixel em (150, 100) na base deve ter alfa 0
        self.assertEqual(base_pixels[150, 100, 3], 0, "Camada base nao deve ser afetada por escrita na duplicada")
        # Pixel em (50, 100) na base deve manter a cor verde original
        self.assertGreater(base_pixels[50, 100, 1], 150, "Camada base deve reter seus pixels verdes intactos")

    # ── 3. Transparent Inactive Layer Decompression in Compositor ─────────────
    def test_03_inactive_layer_compression_and_transparent_decompression(self):
        """Valida que o compositor le transparentemente tiles comprimidos sem falhas visuais."""
        self.facade.select_layer(0)
        self._draw_stroke(30, 30, 220, 30, aen.ColorRGBA(255, 0, 0, 255), size=20.0)

        self.facade.add_layer("Frente Azul")
        self.facade.select_layer(1)
        self._draw_stroke(30, 100, 220, 100, aen.ColorRGBA(0, 0, 255, 255), size=20.0)

        # Captura composicao original
        composite_before = self._get_canvas_array().copy()

        # Comprime a camada inativa (camada 0)
        compressed = self.facade.compress_inactive_layers()
        self.assertGreater(compressed, 0)

        # Compositor acessa os tiles da camada inativa: get_pixel_buffer()
        # O Tile::getBuffer() const deve descomprimir transparentemente em demanda
        composite_after = self._get_canvas_array()

        np.testing.assert_array_equal(
            composite_before,
            composite_after,
            err_msg="A composicao com camadas comprimidas deve ser identica a sem compressao"
        )

    # ── 4. Undo Scratch Disk Paging & Restoration ─────────────────────────────
    def test_04_undo_scratch_disk_paging_and_restoration(self):
        """Valida ativacao do Scratch Disk e restauracao correta de passos de Undo."""
        self.facade.add_layer("Painting")
        self.facade.select_layer(0)

        # Ativa Scratch Disk
        self.facade.set_scratch_disk_enabled(True)
        self.assertTrue(self.facade.is_scratch_disk_enabled())

        # Estado inicial (limpo)
        empty_canvas = self._get_canvas_array().copy()

        # Realiza tracos gerando historico de undo
        self._draw_stroke(40, 40, 100, 40, aen.ColorRGBA(10, 200, 50, 255), size=15.0)
        state1 = self._get_canvas_array().copy()

        self._draw_stroke(40, 80, 100, 80, aen.ColorRGBA(200, 10, 50, 255), size=15.0)
        state2 = self._get_canvas_array().copy()

        # Verifica que o estado 2 contem os dois tracos
        self.assertFalse(np.array_equal(state1, state2))

        # Realiza Undo do estado 2 -> deve voltar ao estado 1
        self.assertTrue(self.facade.can_undo())
        self.facade.undo()
        current_after_undo1 = self._get_canvas_array()
        np.testing.assert_array_equal(state1, current_after_undo1, err_msg="Undo 1 deve restaurar com precisao de pixels")

        # Realiza Undo do estado 1 -> deve voltar ao canvas limpo
        self.assertTrue(self.facade.can_undo())
        self.facade.undo()
        current_after_undo2 = self._get_canvas_array()
        np.testing.assert_array_equal(empty_canvas, current_after_undo2, err_msg="Undo 2 deve restaurar tela limpa")

        # Redo 1 -> deve voltar ao estado 1
        self.assertTrue(self.facade.can_redo())
        self.facade.redo()
        current_after_redo1 = self._get_canvas_array()
        np.testing.assert_array_equal(state1, current_after_redo1, err_msg="Redo 1 deve restaurar estado 1")


if __name__ == "__main__":
    unittest.main()
