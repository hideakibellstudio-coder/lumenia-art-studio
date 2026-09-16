"""Verifica que os flags do pipeline alteram o processamento nativo."""

import os
import sys
import unittest

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import aladyn_engine_native as aen


class TestLowLevelRenderOptions(unittest.TestCase):
    @staticmethod
    def _pixel(facade: aen.PaintEngineFacade):
        return tuple(int(v) for v in np.frombuffer(facade.get_pixel_buffer(), dtype=np.uint8)[:4])

    @staticmethod
    def _two_layer_pixel(src, dst, opacity, linear_gamma, deep_color=False):
        facade = aen.PaintEngineFacade(1, 1)
        facade.set_background_visibility(False)
        facade.add_layer("base")
        facade.select_layer(0)
        facade.paste_rgba_buffer_on_active_layer(0, 0, 1, 1, bytes([*dst, 255]), 0, 1.0)
        facade.add_layer("top")
        facade.select_layer(1)
        facade.set_layer_opacity(1, opacity)
        facade.paste_rgba_buffer_on_active_layer(0, 0, 1, 1, bytes([*src, 255]), 0, 1.0)
        facade.set_render_options(False, linear_gamma, deep_color)
        return TestLowLevelRenderOptions._pixel(facade)

    def test_flags_roundtrip_through_native_facade(self):
        facade = aen.PaintEngineFacade(8, 8)
        facade.set_render_options(True, False, True)
        self.assertTrue(facade.get_low_latency())
        self.assertFalse(facade.get_linear_gamma())
        self.assertTrue(facade.get_deep_color())

    def test_document_generation_invalidates_after_mutation(self):
        facade = aen.PaintEngineFacade(2, 2)
        before = facade.get_document_generation()
        facade.add_layer("paint")
        after_layer = facade.get_document_generation()
        facade.select_layer(0)
        facade.paste_rgba_buffer_on_active_layer(0, 0, 1, 1, bytes([255, 0, 0, 255]))
        after_pixels = facade.get_document_generation()
        self.assertGreater(after_layer, before)
        self.assertGreater(after_pixels, after_layer)

    def test_linear_gamma_changes_compositing_equation(self):
        linear = self._two_layer_pixel([0, 255, 0], [255, 0, 0], 0.5, True)
        srgb = self._two_layer_pixel([0, 255, 0], [255, 0, 0], 0.5, False)
        self.assertGreater(linear[0], 160)
        self.assertGreater(linear[1], 160)
        self.assertLess(srgb[0], 150)
        self.assertLess(srgb[1], 150)
        self.assertNotEqual(linear, srgb)

    def test_deep_color_uses_extended_precision_path(self):
        regular = self._two_layer_pixel([64, 136, 187], [119, 119, 191], 0.7751132147571155, True, False)
        deep = self._two_layer_pixel([64, 136, 187], [119, 119, 191], 0.7751132147571155, True, True)
        self.assertNotEqual(regular, deep)

    def test_low_latency_bypasses_stabilizer_but_keeps_telemetry(self):
        # Quando estabilização <= 0.5%, o atalho de baixa latência desvia o estabilizador (lag < 0.01)
        lag_by_mode_sem_suavizacao = {}
        for low_latency in (False, True):
            facade = aen.PaintEngineFacade(100, 100)
            facade.set_background_visibility(False)
            facade.add_layer("stroke")
            facade.select_layer(0)
            facade.get_stabilizer().set_stabilization_percentage(0.0)
            facade.set_telemetry_enabled(True)
            facade.set_low_latency(low_latency)
            facade.begin_stroke_raw(10.0, 50.0, 1.0, 1.0)
            facade.update_stroke_raw(20.0, 50.0, 1.0, 1.01)
            facade.update_stroke_raw(80.0, 50.0, 1.0, 1.02)
            lag_by_mode_sem_suavizacao[low_latency] = facade.get_telemetry_snapshot().stabilizer_lag_px
            facade.end_stroke_raw()

        self.assertLess(lag_by_mode_sem_suavizacao[True], 0.01)

        # Quando estabilização > 0.5%, a baixa latência respeita a suavização pedida pelo artista
        facade_com_suavizacao = aen.PaintEngineFacade(100, 100)
        facade_com_suavizacao.set_background_visibility(False)
        facade_com_suavizacao.add_layer("stroke")
        facade_com_suavizacao.select_layer(0)
        facade_com_suavizacao.get_stabilizer().set_stabilization_percentage(80.0)
        facade_com_suavizacao.set_telemetry_enabled(True)
        facade_com_suavizacao.set_low_latency(True)
        facade_com_suavizacao.begin_stroke_raw(10.0, 50.0, 1.0, 1.0)
        facade_com_suavizacao.update_stroke_raw(20.0, 50.0, 1.0, 1.01)
        facade_com_suavizacao.update_stroke_raw(80.0, 50.0, 1.0, 1.02)
        lag_com_suavizacao = facade_com_suavizacao.get_telemetry_snapshot().stabilizer_lag_px
        facade_com_suavizacao.end_stroke_raw()

        self.assertGreater(lag_com_suavizacao, 1.0)


if __name__ == "__main__":
    unittest.main()
