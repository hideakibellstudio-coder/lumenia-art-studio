"""
Low-Level Test Suite: Phase 5 - 120 FPS Viewport Pipeline & Hardware Acceleration
Validates:
1. Dirty Tile Tracking & Zero-Copy Sub-Texture Streaming
2. ViewportTransform 2D Analytical Matrix Math & Coordinate Invertibility
3. Frustum Culling & Visible Tile Range Computation
4. Hardware Accelerated Viewport Instantiation & Fallback Telemetry
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6 import QtWidgets
import aladyn_engine_native as aen

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)


class TestPhase5ViewportPipeline(unittest.TestCase):
    def setUp(self):
        self.w = 512
        self.h = 512
        self.facade = aen.PaintEngineFacade(self.w, self.h)
        self.facade.set_background_visibility(False)

    def _draw_stroke(self, x0, y0, x1, y1, color: aen.ColorRGBA, size=20.0, steps=20):
        profile: aen.BrushProfile = self.facade.get_brush_profile()
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

    # ── 1. Dirty Tile Tracking & Sub-Texture Streaming ────────────────────────
    def test_01_dirty_tile_tracking_and_clearing(self):
        """Valida que o motor rastreia com precisao os tiles modificados e reseta sob demanda."""
        self.facade.select_layer(0)
        self.facade.clear_dirty_tiles()
        self.assertEqual(len(self.facade.get_dirty_tile_indices()), 0)

        # Desenha um traço que cruza do tile (0, 0) para o tile (1, 1) (128x128 cada)
        # De (20, 20) até (180, 180)
        self._draw_stroke(20, 20, 180, 180, aen.ColorRGBA(255, 0, 0, 255), size=24.0)

        dirty_tiles = self.facade.get_dirty_tile_indices()
        self.assertGreater(len(dirty_tiles), 0, "Deveria haver tiles marcados como sujos")

        # Tile (0, 0) e Tile (1, 1) devem estar na lista de sujos
        tile_coords = set(dirty_tiles)
        self.assertIn((0, 0), tile_coords, "Tile (0, 0) deve ter sido modificado pelo inicio do traço")
        self.assertIn((1, 1), tile_coords, "Tile (1, 1) deve ter sido modificado pelo final do traço")

        # Reseta os flags de dirty (simulando upload para textura de GPU)
        self.facade.clear_dirty_tiles()
        self.assertEqual(len(self.facade.get_dirty_tile_indices()), 0, "Apos clear, nenhum tile deve constar como dirty")

    # ── 2. ViewportTransform Analytical Math & Invertibility ──────────────────
    def test_02_viewport_transform_coordinate_roundtrip(self):
        """Valida a reversibilidade analítica exata da projeção Tela <-> Canvas sob zoom e rotação."""
        vt = aen.ViewportTransform(1920.0, 1080.0, 3840.0, 2160.0)

        test_cameras = [
            (0.0, 0.0, 1.0, 0.0),       # Padrão
            (150.0, -80.0, 2.5, 35.0),  # Zoom in com rotação oblíqua
            (-200.0, 120.0, 0.4, 90.0), # Zoom out com rotação reta
            (50.0, 50.0, 1.5, 180.0),   # Rotação invertida
            (-30.0, 75.0, 3.2, -45.0),  # Rotação negativa
        ]

        test_points = [
            (0.0, 0.0),
            (1920.0, 1080.0),
            (3840.0, 2160.0),
            (500.25, 800.75),
            (1234.5, 678.9),
        ]

        for pan_x, pan_y, zoom, rot in test_cameras:
            vt.set_camera(pan_x, pan_y, zoom, rot)
            for cx, cy in test_points:
                sx, sy = vt.canvas_to_screen(cx, cy)
                rcx, rcy = vt.screen_to_canvas(sx, sy)

                self.assertAlmostEqual(
                    cx, rcx, places=4,
                    msg=f"Falha de inversibilidade em X para camera (zoom={zoom}, rot={rot}): {cx} != {rcx}"
                )
                self.assertAlmostEqual(
                    cy, rcy, places=4,
                    msg=f"Falha de inversibilidade em Y para camera (zoom={zoom}, rot={rot}): {cy} != {rcy}"
                )

    # ── 3. Viewport Frustum Culling & Visible Tile Range ──────────────────────
    def test_03_viewport_frustum_culling_and_tile_range(self):
        """Valida o descarte de tiles fora do campo de visão (Frustum Culling) em canvas 4K."""
        # Viewport de 800x600 sobre canvas 4K (3840x2160)
        # Em 3840x2160 com tiles de 128x128, ha 30x17 = 510 tiles totais.
        vt = aen.ViewportTransform(800.0, 600.0, 3840.0, 2160.0)

        # Câmera com zoom 4.0 focada na origem (canto superior esquerdo)
        # No zoom 4.0, o viewport 800x600 enxerga apenas 200x150 pixels do canvas
        # Pan centralizado no canto (0, 0)
        vt.set_camera(400.0, 300.0, 4.0, 0.0)

        min_tx, min_ty, max_tx, max_ty = vt.get_visible_tile_range(128, 30, 17)

        # Apenas uma fração mínima dos tiles deve estar visível (cerca de 3 tiles em X e 2 tiles em Y)
        visible_tiles_x = max_tx - min_tx + 1
        visible_tiles_y = max_ty - min_ty + 1
        total_visible = visible_tiles_x * visible_tiles_y

        self.assertLessEqual(visible_tiles_x, 4, "No zoom 4x, poucos tiles devem ser visiveis horizontalmente")
        self.assertLessEqual(visible_tiles_y, 4, "No zoom 4x, poucos tiles devem ser visiveis verticalmente")
        self.assertLess(total_visible, 20, "Frustum Culling deve descartar mais de 95% dos 510 tiles do canvas 4K")

        # Verifica teste booleano de visibilidade individual
        self.assertTrue(vt.is_tile_visible(min_tx, min_ty, 128), "Tile dentro do frustum deve ser visivel")
        self.assertFalse(vt.is_tile_visible(0, 0, 128), "Tile (0, 0) fora do frustum deve ser descartado pelo culling")
        self.assertFalse(vt.is_tile_visible(28, 15, 128), "Tile distante (28, 15) deve ser descartado pelo culling")

    # ── 4. RenderWidget Hardware Acceleration & Telemetry ─────────────────────
    def test_04_render_widget_hardware_acceleration_and_telemetry(self):
        """Valida inicializacao do RenderWidget acelerado/fallback e metricas de Viewport."""
        from ui.plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget

        widget = RenderWidget()
        widget.resize(800, 600)

        # Verifica tipo de widget (QOpenGLWidget se GPU ativa, QWidget se fallback)
        self.assertTrue(isinstance(widget, QtWidgets.QWidget))

        # Telemetria do viewport
        telem = widget.get_viewport_telemetry()
        self.assertIn("is_gpu_accelerated", telem)
        self.assertIn("renderer_type", telem)
        self.assertIn("qt_fps", telem)
        self.assertIn("qt_paint_total_ms", telem)

        # Renderização não deve falhar
        img = widget.get_canvas_image()
        self.assertIsNotNone(img)
        self.assertFalse(img.isNull())
        widget.close()


if __name__ == "__main__":
    unittest.main()
