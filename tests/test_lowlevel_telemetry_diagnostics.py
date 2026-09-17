"""
Low-Level Test Suite: High-Performance Engine Telemetry & Diagnostic Cockpit
Validates zero-overhead C++ metrics capturing, clean-memory enable/disable toggling,
stroke latency (µs) measurement, TileGrid / UndoStack RAM tracking, and UI dialog instantiation.
"""

import os
import sys
import unittest
import numpy as np

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
        from plugins.ui.telemetry_plugin.panel import TelemetryPanel

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

    # ── 6. Grid Window State Transitions & Comprehensive Report ───────────────
    def test_06_grid_window_state_transitions_and_report(self):
        """Valida que o TelemetryGridWindow rastreia transições de estado (gargalo vs equilibrado)
        e gera o relatório completo com os 20 medidores do Grid."""
        from PySide6 import QtWidgets
        app = QtWidgets.QApplication.instance()
        if not app:
            app = QtWidgets.QApplication(sys.argv)

        from ui.core.dialogs.telemetry_grid_window import TelemetryGridWindow
        grid_win: TelemetryGridWindow = TelemetryGridWindow()
        self.assertIsNotNone(grid_win)
        self.assertEqual(len(grid_win._cards), 20, "Deve conter exatamente 20 cards métricos no Grid")

        # 1. Estado inicial equilibrado
        self.assertEqual(grid_win._current_state_key, "PIPELINE_EQUILIBRADO")
        self.assertIn("PIPELINE EQUILIBRADO", grid_win.lbl_bottleneck.text())

        # 2. Simula detecção de gargalo em Raster (> 15000 µs)
        grid_win._update_bottleneck_banner(dab_us=23574.7, und_us=5.2, cmp_us=1112.3, blit_ms=0.15)
        self.assertEqual(grid_win._current_state_key, "GARGALO_RASTER")
        self.assertIn("GARGALO EM RASTER", grid_win.lbl_bottleneck.text())
        self.assertEqual(grid_win._state_counts["GARGALO_RASTER"], 1)

        # 3. Simula retorno ao estado equilibrado (< 2ms)
        grid_win._update_bottleneck_banner(dab_us=850.0, und_us=5.0, cmp_us=500.0, blit_ms=0.15)
        self.assertEqual(grid_win._current_state_key, "PIPELINE_EQUILIBRADO")
        self.assertIn("PIPELINE EQUILIBRADO", grid_win.lbl_bottleneck.text())
        self.assertGreaterEqual(len(grid_win._state_history), 3, "Deve registrar histórico de transições")

        # 4. Geração do relatório completo
        report = grid_win.generate_full_report()
        self.assertIn("COCKPIT DE TELEMETRIA & DIAGNÓSTICO EM GRID", report)
        self.assertIn("DIAGNÓSTICO DO PIPELINE & ALTERAÇÕES DE ESTADO", report)
        self.assertIn("GARGALO EM RASTER", report)
        self.assertIn("Resumo de Ocorrências na Sessão de Teste:", report)
        self.assertIn("Picos Máximos de Estresse Registrados na Sessão:", report)
        self.assertIn("DECOMPOSIÇÃO PROPORCIONAL DO PIPELINE", report)
        self.assertIn("PAINEL COMPLETO EM GRID (TODOS OS 20 MEDIDORES EM TEMPO REAL)", report)

        # Verifica que todos os 20 títulos de cards estão presentes no relatório
        for card in grid_win._cards:
            self.assertIn(card.title, report)

        # 5. Valida o reset de métricas e histórico
        grid_win._on_reset_metrics()
        self.assertEqual(grid_win._current_state_key, "PIPELINE_EQUILIBRADO")
        self.assertEqual(grid_win._state_counts["GARGALO_RASTER"], 0)
        grid_win.close()

    # ── 7. Unified TelemetryTracker & All Copy Buttons ───────────────────────
    def test_07_all_copy_buttons_generate_identical_full_report(self):
        """Valida que o TelemetryTracker unifica todos os botões de cópia (Cockpit, Painel e Diálogo)
        garantindo que todos copiem exatamente o relatório completo com 20 medidores e histórico de transições."""
        from PySide6 import QtWidgets
        app = QtWidgets.QApplication.instance()
        if not app:
            app = QtWidgets.QApplication(sys.argv)

        from ui.core.engine.telemetry_tracker import TelemetryTracker
        from plugins.ui.telemetry_plugin.panel import TelemetryPanel
        from ui.core.dialogs.telemetry_diagnostics_dialog import TelemetryDiagnosticsDialog

        tracker = TelemetryTracker.instance()
        tracker.reset()

        # Simula transição para gargalo de raster
        snap = self.facade.get_telemetry_snapshot()
        tracker.update(snap, {"qt_draw_image_ms": 1.5, "qt_fps": 60.0})
        tracker.record_state_transition(
            new_state="⚠️ GARGALO EM RASTER: PINCEL GRANDE (> 15ms / CPU SATURADA)",
            state_key="GARGALO_RASTER",
            cause="Teste de Estresse com 1000 dabs",
        )

        # 1. Gera relatório a partir do TelemetryTracker
        report_tracker = tracker.generate_full_report()
        self.assertIn("DIAGNÓSTICO DO PIPELINE & ALTERAÇÕES DE ESTADO", report_tracker)
        self.assertIn("GARGALO EM RASTER", report_tracker)
        self.assertIn("DECOMPOSIÇÃO PROPORCIONAL DO PIPELINE", report_tracker)
        self.assertIn("PAINEL COMPLETO EM GRID", report_tracker)

        # 2. Testa botão de cópia do TelemetryPanel
        panel = TelemetryPanel()
        self.assertTrue(hasattr(panel, "btn_copy_report"), "TelemetryPanel deve possuir botão de copiar relatório")
        self.assertTrue(hasattr(panel, "_on_copy_report"))

        # 3. Testa diálogo avançado TelemetryDiagnosticsDialog
        dlg = TelemetryDiagnosticsDialog()
        self.assertTrue(hasattr(dlg, "_copy_diagnostic_report"))
        dlg.close()


if __name__ == "__main__":
    unittest.main()
