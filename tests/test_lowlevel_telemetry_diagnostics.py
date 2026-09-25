"""
Low-Level Test Suite: High-Performance Engine Telemetry & Diagnostic Cockpit
Validates zero-overhead C++ metrics capturing, clean-memory enable/disable toggling,
stroke latency (µs) measurement, TileGrid / UndoStack RAM tracking, and UI dialog instantiation.
"""

import os
import sys
import unittest

# Raiz do projeto Lumenia
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import aladyn_engine_native as aen


class TestLowLevelTelemetryDiagnostics(unittest.TestCase):
    def setUp(self):
        self.w = 300
        self.h = 300
        self.facade = aen.PaintEngineFacade(self.w, self.h)
        self.facade.add_layer("Camada Telemetria")
        self.facade.select_layer(0)

    # ── 1. Telemetry Default State (Zero-Overhead Standby) ────────────────────
    def test_01_telemetry_default_state_is_disabled(self):
        """Valida que a telemetria nasce desligada por padrão (Zero-Cost)."""
        self.assertFalse(self.facade.is_telemetry_enabled())
        self.assertFalse(self.facade.is_detailed_logging_enabled())

        snap: aen.RealTimeStrokeMetrics = self.facade.get_telemetry_snapshot()
        self.assertIsNotNone(snap)
        self.assertEqual(snap.total_dabs_in_stroke, 0)
        self.assertEqual(snap.last_segment_latency_us, 0.0)

    # ── 2. Enable & Capture Metrics During Drawing ────────────────────────────
    def test_02_enable_and_capture_stroke_metrics(self):
        """Valida captura em tempo real de latência, dabs, tiles e memória ao ativar a telemetria."""
        self.facade.set_telemetry_enabled(True)
        self.assertTrue(self.facade.is_telemetry_enabled())

        # Configura pincel Inker
        self.facade.set_engine_type(int(aen.EngineType.Inker))
        profile = self.facade.get_brush_profile()
        profile.brush_size = 16.0
        profile.opacity = 1.0
        profile.base_color = aen.ColorRGBA(255, 0, 0, 255)

        # Executa traço de (30, 30) a (200, 200) com 20 passos
        self.facade.begin_stroke_raw(30.0, 30.0, 0.8)
        for i in range(1, 21):
            t = i / 20.0
            x = 30.0 + (200.0 - 30.0) * t
            y = 30.0 + (200.0 - 30.0) * t
            self.facade.update_stroke_raw(x, y, 0.8)
        self.facade.end_stroke_raw()

        snap = self.facade.get_telemetry_snapshot()
        self.assertIsNotNone(snap)

        # Validações métricas
        self.assertGreater(snap.total_dabs_in_stroke, 0, "Deve registrar dabs executados no traço")
        self.assertGreater(snap.last_segment_latency_us, 0.0, "Latência do último segmento deve ser > 0 µs")
        self.assertGreater(snap.active_tile_count, 0, "Deve registrar tiles alocados na camada")
        self.assertGreater(snap.tile_grid_memory_mb, 0.0, "RAM do TileGrid deve ser > 0 MB")
        self.assertGreater(snap.undo_stack_memory_mb, 0.0, "RAM do UndoStack deve ser > 0 MB")
        self.assertEqual(snap.undo_steps_count, 1, "Deve registrar 1 passo de histórico no UndoManager")

    # ── 3. Clean-Memory Toggle (Desativação e Limpeza) ────────────────────────
    def test_03_clean_memory_disable_toggle(self):
        """Valida que desativar a telemetria zera os contadores e limpa memória temporária."""
        self.facade.set_telemetry_enabled(True)
        self.facade.begin_stroke_raw(50.0, 50.0, 1.0)
        self.facade.update_stroke_raw(100.0, 100.0, 1.0)
        self.facade.end_stroke_raw()

        # Desativa telemetria
        self.facade.set_telemetry_enabled(False)
        self.assertFalse(self.facade.is_telemetry_enabled())

        snap_after = self.facade.get_telemetry_snapshot()
        self.assertEqual(snap_after.total_dabs_in_stroke, 0, "Contador de dabs deve ser zerado")
        self.assertEqual(snap_after.last_segment_latency_us, 0.0, "Latência deve ser zerada")

    # ── 4. UI Diagnostics Dialog & Panel Instantiation ───────────────────────
    def test_04_ui_dialog_and_panel_instantiation(self):
        """Valida que o TelemetryDiagnosticsDialog e o TelemetryPanel inicializam perfeitamente."""
        from PySide6 import QtWidgets
        app = QtWidgets.QApplication.instance()
        if not app:
            app = QtWidgets.QApplication(sys.argv)

        from ui.core.dialogs.telemetry_diagnostics_dialog import TelemetryDiagnosticsDialog
        from ui.plugins.panels.telemetry_plugin.panel import TelemetryPanel

        panel = TelemetryPanel()
        self.assertIsNotNone(panel)
        self.assertFalse(panel._is_capturing)

        # Testa o clique no botão mestre de ativação do painel
        panel._on_toggle_capture()
        self.assertTrue(panel._is_capturing)
        self.assertTrue(panel._timer.isActive())

        # Desativa
        panel._on_toggle_capture()
        self.assertFalse(panel._is_capturing)
        self.assertFalse(panel._timer.isActive())

        # Instancia o diálogo de diagnóstico
        dlg = TelemetryDiagnosticsDialog()
        self.assertEqual(dlg.tabs.count(), 5, "Diálogo deve conter 5 abas diagnósticas incluindo Pipeline Granular")
        dlg.close()

    # ── 5. Granular Pipeline Stages & Viewport Metrics ────────────────────────
    def test_05_granular_pipeline_stages_metrics(self):
        """Valida a decomposição granular nos 5 estágios C++ e geometria de carimbos."""
        self.facade.set_telemetry_enabled(True)
        self.facade.set_engine_type(int(aen.EngineType.Brush))

        self.facade.begin_stroke_raw(50.0, 50.0, 1.0, 1.0)
        self.facade.update_stroke_raw(70.0, 70.0, 1.0, 1.01)
        self.facade.update_stroke_raw(90.0, 90.0, 1.0, 1.02)
        self.facade.end_stroke_raw()

        snap = self.facade.get_telemetry_snapshot()
        self.assertIsNotNone(snap)

        # Decomposição granular do pipeline (µs)
        self.assertGreaterEqual(snap.time_kinematics_us, 0.0, "Tempo de cinemática deve ser medido (µs)")
        self.assertGreaterEqual(snap.time_interpolation_us, 0.0, "Tempo de interpolação deve ser medido (µs)")
        self.assertGreater(snap.time_raster_dab_us, 0.0, "Tempo de rasterização de dabs deve ser > 0 µs")
        self.assertGreater(snap.time_undo_record_us, 0.0, "Tempo de gravação de undo deve ser > 0 µs")
        self.assertGreater(snap.time_composite_us, 0.0, "Tempo de composição de camadas deve ser > 0 µs")

        # Pegada geométrica
        self.assertGreater(snap.last_dabs_rendered, 0, "Dabs renderizados no segmento deve ser > 0")
        self.assertGreater(snap.last_dirty_width, 0.0, "Largura da região suja deve ser > 0 px")
        self.assertGreater(snap.last_dirty_height, 0.0, "Altura da região suja deve ser > 0 px")
        self.assertGreater(snap.last_dirty_area_px, 0.0, "Área suja deve ser > 0 px²")
        self.assertGreater(snap.last_tiles_recorded, 0, "Tiles gravados no undo deve ser > 0")
        self.assertGreater(snap.last_tiles_composited, 0, "Tiles compostos deve ser > 0")

    # ── 6. Snapshot nativo → DTO → relatório único ───────────────────────────
    def test_06_native_snapshot_feeds_tracker_and_report(self):
        """O snapshot nativo de um traço real vira DTO, alimenta o TelemetryTracker
        e aparece no relatório único (o mesmo dos três botões "Copiar")."""
        from ui.core.engine.telemetry_dto import TelemetrySnapshot
        from ui.core.engine.telemetry_report import build_report
        from ui.core.engine.telemetry_tracker import TelemetryTracker

        self.facade.set_telemetry_enabled(True)
        self.facade.begin_stroke_raw(50.0, 50.0, 1.0)
        for i in range(1, 40):
            self.facade.update_stroke_raw(50.0 + i * 4, 50.0 + i * 2, 0.9)
        snap = TelemetrySnapshot.from_native(self.facade.get_telemetry_snapshot())
        self.facade.end_stroke_raw()
        self.assertGreater(snap.last_dabs_rendered, 0)
        self.assertGreater(snap.raw_pressure, 0.0)

        tracker = TelemetryTracker.instance()
        tracker.reset()
        try:
            tracker.update(snap, {"qt_draw_image_ms": 1.5, "qt_fps": 60.0})
            self.assertGreater(tracker.peaks["motor_latency_us"], 0.0)
            self.assertGreater(tracker.last_active_pen["raw_pressure"], 0.0)
            report = build_report(tracker, snap, {"qt_draw_image_ms": 1.5, "qt_fps": 60.0})
            self.assertIn(f"{snap.last_dabs_rendered} dabs", report)
            self.assertIn("PAINEL COMPLETO EM GRID", report)
        finally:
            tracker.reset()


if __name__ == "__main__":
    unittest.main()
