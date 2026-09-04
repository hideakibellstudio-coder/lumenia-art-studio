"""
Teste de Validação e Integridade do StabilizerLabPlugin e StabilizerHub.
========================================================================
Testa os motores matemáticos, a diluição de sensibilidade por perfis sem zonas
mortas e a sincronização entre a barra do topo e a doca.
"""

import sys
import os
import math
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from ui.core.engine.stabilizer_hub import StabilizerHub
from plugins.ui.stabilizer_lab_plugin.algorithms import (
    AdaptiveProfileStabilizerEngine,
    LumeniaBaselineEngine,
    SaiStabilizerEngine,
    InfinitePainterKalmanEngine
)
from plugins.ui.stabilizer_lab_plugin import StabilizerLabPlugin


class TestStabilizerLab(unittest.TestCase):

    def test_stabilizer_hub_linear_dilution(self):
        hub = StabilizerHub.instance()

        # Selecionar 'lineart' define o slider para o padrão de 65%
        hub.set_profile("lineart")
        self.assertEqual(hub.current_profile, "lineart")
        self.assertEqual(hub.fine_tuning_pct, 65)

        # Selecionar 'fluid' define o slider para 20%
        hub.set_profile("fluid")
        self.assertEqual(hub.current_profile, "fluid")
        self.assertEqual(hub.fine_tuning_pct, 20)

        # Arrastar o slider para 85% infere automaticamente 'sculpted' (Super 1)
        hub.set_fine_tuning_pct(85)
        self.assertEqual(hub.current_profile, "sculpted")
        p85 = hub.get_calculated_params()
        self.assertGreater(p85["buffer_capacity"], 35)

        # Arrastar o slider para 100% infere 'silk' (Super 2)
        hub.set_fine_tuning_pct(100)
        self.assertEqual(hub.current_profile, "silk")
        p_silk = hub.get_calculated_params()
        self.assertEqual(p_silk["buffer_capacity"], 140)
        self.assertAlmostEqual(p_silk["alpha"], 0.028, places=3)

        # Arrastar o slider para 0% infere 'off'
        hub.set_fine_tuning_pct(0)
        self.assertEqual(hub.current_profile, "off")
        p0 = hub.get_calculated_params()
        self.assertEqual(p0["buffer_capacity"], 1)

    def test_adaptive_profile_engine_execution(self):
        hub = StabilizerHub.instance()
        hub.set_profile("lineart")
        hub.set_fine_tuning_pct(50)

        engine = AdaptiveProfileStabilizerEngine()
        engine.reset(10.0, 10.0, 0.5)

        for i in range(1, 20):
            raw_x = 10.0 + i * 5.0
            raw_y = 10.0 + i * 2.5
            out_x, out_y, out_p = engine.update(raw_x, raw_y, 0.5)
            self.assertFalse(math.isnan(out_x))
            self.assertFalse(math.isnan(out_y))
            self.assertLess(out_x, raw_x)

        # Flush
        flush_pts = engine.flush()
        self.assertGreater(len(flush_pts), 0)
        self.assertAlmostEqual(flush_pts[-1][0], 105.0, delta=0.5)

    def test_lumenia_baseline_engine(self):
        engine = LumeniaBaselineEngine(percentage=50.0, weight_exponent=1.25)
        engine.reset(10.0, 10.0, 0.5)

        for i in range(1, 11):
            raw_x = 10.0 + i * 5.0 + (1.0 if i % 2 == 0 else -1.0)
            raw_y = 10.0 + i * 5.0
            out_x, out_y, out_p = engine.update(raw_x, raw_y, 0.5)
            self.assertFalse(math.isnan(out_x))
            self.assertFalse(math.isnan(out_y))
            self.assertEqual(out_p, 0.5)

        flush_pts = engine.flush(steps=3)
        self.assertEqual(len(flush_pts), 3)

    def test_sai_stabilizer_engine(self):
        engine = SaiStabilizerEngine(level=5, gamma=1.4, smooth_pressure=True)
        self.assertEqual(engine.buffer_capacity, int(2 + 5 * 1.7))
        self.assertAlmostEqual(engine.alpha, 1.0 / (1.0 + 5 * 0.30), places=3)

        engine.reset(0.0, 0.0, 0.2)

        for i in range(1, 25):
            raw_x = float(i * 10)
            raw_y = float(i * 5)
            raw_p = 0.5 + (0.1 if i % 2 == 0 else -0.1)
            out_x, out_y, out_p = engine.update(raw_x, raw_y, raw_p)

            self.assertFalse(math.isnan(out_x))
            self.assertFalse(math.isnan(out_y))
            self.assertFalse(math.isnan(out_p))
            self.assertLess(out_x, raw_x)
            if i > 5:
                self.assertLess(abs(out_p - 0.5), 0.05)

        flush_pts = engine.flush()
        self.assertGreater(len(flush_pts), 0)
        last_pt = flush_pts[-1]
        self.assertAlmostEqual(last_pt[0], 240.0, delta=0.3)

    def test_infinite_painter_kalman_engine(self):
        engine = InfinitePainterKalmanEngine(sigma_process=0.01, sigma_measurement=1.0, jerk_exponent=8.0)
        engine.reset(100.0, 100.0, 0.5)

        for i in range(1, 30):
            raw_x = 100.0 + i * 4.0
            raw_y = 100.0 + math.sin(i * 0.5) * 20.0
            out_x, out_y, out_p = engine.update(raw_x, raw_y, 0.5)
            self.assertFalse(math.isnan(out_x))
            self.assertFalse(math.isnan(out_y))

        self.assertGreater(engine.last_vel_norm, 0.0)

    def test_plugin_metadata_and_switching(self):
        plugin = StabilizerLabPlugin()
        meta = plugin.get_metadata()
        self.assertEqual(meta.id, "lumenia.stabilizer_lab")

        plugin.set_engine_mode("profiles")
        pt1 = plugin.process_stroke_point(10.0, 10.0, 0.5, 0.0)
        self.assertEqual(len(pt1), 3)

        plugin.set_engine_mode("kalman")
        pt2 = plugin.process_stroke_point(15.0, 15.0, 0.5, 0.0)
        self.assertEqual(len(pt2), 3)

        plugin.set_engine_mode("baseline")
        pt3 = plugin.process_stroke_point(20.0, 20.0, 0.5, 0.0)
        self.assertEqual(len(pt3), 3)


if __name__ == "__main__":
    unittest.main()
