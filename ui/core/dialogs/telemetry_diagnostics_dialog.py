"""
TelemetryDiagnosticsDialog — Diálogo Avançado de Diagnóstico & Telemetria do ALADYN ENGINE
========================================================================================
Janela frameless padronizada (Design System Lumenia V2) para auditoria de desempenho em tempo real:
- Latência por segmento de traço (microssegundos)
- Frequência de amostragem da mesa digitalizadora (Hz) e taxa de dabs/s
- Memória de blocos raster (Tiles 64x64) e consumo da pilha de Undo/Redo
- Curva cinemática da caneta (Pressão física vs Modulada, Lag do Estabilizador)
- Configuração de verbosidade de logs do terminal e Benchmark sintético de renderização
"""

from __future__ import annotations

import time
from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.theme.manager import ThemeManager
from ui.core.engine.registry import EngineRegistry
from ui.core.dialogs.telemetry_diagnostics_cards import StatCard
from ui.core.engine.telemetry_dto import TelemetrySnapshot


class TelemetryDiagnosticsDialog(BaseFramelessDialog):
    """Diálogo completo de auditoria e diagnóstico do motor nativo."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(
            title="Diagnóstico & Telemetria do Motor",
            icon_name="chart",
            parent=parent,
            modal=True,
        )
        self.resize(720, 540)
        self.setMinimumSize(600, 440)
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)  # 30 FPS polling
        self._timer.timeout.connect(self._refresh_metrics)

        self._build_content()
        from ui.core.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()
        self._timer.start()

    def _build_content(self) -> None:
        # Layout principal com Abas
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setObjectName("TelemetryTabs")

        # ── 1. Aba: Desempenho em Tempo Real ──────────────────────────────────
        tab_perf = QtWidgets.QWidget()
        lo_perf = QtWidgets.QVBoxLayout(tab_perf)
        lo_perf.setContentsMargins(12, 12, 12, 12)
        lo_perf.setSpacing(12)

        grid_perf = QtWidgets.QGridLayout()
        grid_perf.setSpacing(10)

        self.card_latency = StatCard("Latência do Motor (C++)", "0.00 µs")
        self.card_dabs_sec = StatCard("Taxa de Carimbos", "0 dabs/s")
        self.card_stylus_hz = StatCard("Frequência da Mesa", "0 Hz")
        self.card_stroke_time = StatCard("Duração do Traço", "0.0 ms")

        grid_perf.addWidget(self.card_latency, 0, 0)
        grid_perf.addWidget(self.card_dabs_sec, 0, 1)
        grid_perf.addWidget(self.card_stylus_hz, 1, 0)
        grid_perf.addWidget(self.card_stroke_time, 1, 1)
        lo_perf.addLayout(grid_perf)

        # Informações de Hardware & Aceleração
        grp_hw = QtWidgets.QGroupBox("Aceleração de Hardware & Motor")
        lo_hw = QtWidgets.QFormLayout(grp_hw)
        lo_hw.setContentsMargins(12, 12, 12, 12)
        lo_hw.setSpacing(8)

        self.lbl_simd_status = QtWidgets.QLabel("AVX2 / SSE2 Ativo (Vetorizado)")
        succ_col = ThemeManager.instance().get_color("success", "#10b981")
        self.lbl_simd_status.setStyleSheet(f"color: {succ_col}; font-weight: bold;")
        self.lbl_engine_active = QtWidgets.QLabel("InkerEngine (Rasterizador SIMD)")
        lo_hw.addRow("Conjunto de Instruções:", self.lbl_simd_status)
        lo_hw.addRow("Mini-Motor Ativo:", self.lbl_engine_active)
        lo_perf.addWidget(grp_hw)
        lo_perf.addStretch()

        self.tabs.addTab(tab_perf, "📈 Desempenho")

        # ── 2. Aba: Memória & Blocos (Tiles) ──────────────────────────────────
        tab_mem = QtWidgets.QWidget()
        lo_mem = QtWidgets.QVBoxLayout(tab_mem)
        lo_mem.setContentsMargins(12, 12, 12, 12)
        lo_mem.setSpacing(12)

        grid_mem = QtWidgets.QGridLayout()
        grid_mem.setSpacing(10)

        self.card_tiles_count = StatCard("Tiles Alocados (64x64)", "0")
        self.card_canvas_ram = StatCard("RAM do Documento", "0.00 MB")
        self.card_undo_ram = StatCard("RAM do Histórico (Undo)", "0.00 MB")
        self.card_undo_steps = StatCard("Passos de Desfazer", "0")

        grid_mem.addWidget(self.card_tiles_count, 0, 0)
        grid_mem.addWidget(self.card_canvas_ram, 0, 1)
        grid_mem.addWidget(self.card_undo_ram, 1, 0)
        grid_mem.addWidget(self.card_undo_steps, 1, 1)
        lo_mem.addLayout(grid_mem)

        # Ações de Otimização de Memória
        grp_opt = QtWidgets.QGroupBox("Gestão & Limpeza de Memória")
        lo_opt = QtWidgets.QHBoxLayout(grp_opt)
        lo_opt.setContentsMargins(12, 12, 12, 12)

        self.btn_clear_undo = QtWidgets.QPushButton("🧹 Limpar Histórico de Desfazer")
        self.btn_clear_undo.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clear_undo.clicked.connect(self._on_clear_undo)
        lo_opt.addWidget(self.btn_clear_undo)
        lo_mem.addWidget(grp_opt)
        lo_mem.addStretch()

        self.tabs.addTab(tab_mem, "🧠 Memória & Tiles")

        # ── 3. Aba: Pipeline Granular & Viewport ──────────────────────────────
        tab_pipe = QtWidgets.QWidget()
        lo_pipe = QtWidgets.QVBoxLayout(tab_pipe)
        lo_pipe.setContentsMargins(12, 12, 12, 12)
        lo_pipe.setSpacing(10)

        grp_stages = QtWidgets.QGroupBox("Decomposição do Pipeline em Microssegundos (µs)")
        lo_stages = QtWidgets.QGridLayout(grp_stages)
        lo_stages.setContentsMargins(10, 10, 10, 10)
        lo_stages.setSpacing(8)

        self.card_stage_kin = StatCard("1. Cinemática / Dinâmica", "0.0 µs")
        self.card_stage_int = StatCard("2. Interpolação Dabs", "0.0 µs")
        self.card_stage_dab = StatCard("3. RasterDab (Shaders)", "0.0 µs")
        self.card_stage_und = StatCard("4. Undo Record (Tiles)", "0.0 µs")
        self.card_stage_cmp = StatCard("5. Compositor Camadas", "0.0 µs")
        self.card_stage_blt = StatCard("6. Apresentação Blit Qt", "0.00 ms")

        lo_stages.addWidget(self.card_stage_kin, 0, 0)
        lo_stages.addWidget(self.card_stage_int, 0, 1)
        lo_stages.addWidget(self.card_stage_dab, 0, 2)
        lo_stages.addWidget(self.card_stage_und, 1, 0)
        lo_stages.addWidget(self.card_stage_cmp, 1, 1)
        lo_stages.addWidget(self.card_stage_blt, 1, 2)
        lo_pipe.addWidget(grp_stages)

        grp_geom = QtWidgets.QGroupBox("Pegada Geométrica e Taxa Real da Tela")
        lo_geom = QtWidgets.QGridLayout(grp_geom)
        lo_geom.setContentsMargins(10, 10, 10, 10)
        lo_geom.setSpacing(8)

        self.card_vp_fps = StatCard("Taxa Real da Viewport", "0.0 FPS")
        self.card_vp_dirty = StatCard("Região Repintada (Último Blit)", "0 × 0 px")
        self.card_vp_tiles = StatCard("Tiles Gravados (Segmento)", "0 tiles")
        self.card_vp_dabs = StatCard("Dabs Emitidos (Segmento)", "0 dabs")

        lo_geom.addWidget(self.card_vp_fps, 0, 0)
        lo_geom.addWidget(self.card_vp_dirty, 0, 1)
        lo_geom.addWidget(self.card_vp_tiles, 1, 0)
        lo_geom.addWidget(self.card_vp_dabs, 1, 1)
        lo_pipe.addWidget(grp_geom)
        lo_pipe.addStretch()

        self.tabs.addTab(tab_pipe, "🔬 Pipeline & Viewport")

        # ── 4. Aba: Sensor & Cinemática da Caneta ────────────────────────────
        tab_pen = QtWidgets.QWidget()
        lo_pen = QtWidgets.QVBoxLayout(tab_pen)
        lo_pen.setContentsMargins(12, 12, 12, 12)
        lo_pen.setSpacing(12)

        grid_pen = QtWidgets.QGridLayout()
        grid_pen.setSpacing(10)

        self.card_raw_press = StatCard("Pressão Física Bruta", "0 %")
        self.card_dyn_press = StatCard("Pressão Modulada", "0 %")
        self.card_velocity = StatCard("Velocidade do Traço", "0 px/s")
        self.card_lag = StatCard("Lag do Estabilizador", "0.0 px")

        grid_pen.addWidget(self.card_raw_press, 0, 0)
        grid_pen.addWidget(self.card_dyn_press, 0, 1)
        grid_pen.addWidget(self.card_velocity, 1, 0)
        grid_pen.addWidget(self.card_lag, 1, 1)
        lo_pen.addLayout(grid_pen)
        lo_pen.addStretch()

        self.tabs.addTab(tab_pen, "🖋️ Caneta & Sensor")

        # ── 4. Aba: Logs & Benchmark ──────────────────────────────────────────
        tab_tools = QtWidgets.QWidget()
        lo_tools = QtWidgets.QVBoxLayout(tab_tools)
        lo_tools.setContentsMargins(12, 12, 12, 12)
        lo_tools.setSpacing(12)

        grp_logs = QtWidgets.QGroupBox("Configurações de Log no Terminal")
        lo_grp_logs = QtWidgets.QVBoxLayout(grp_logs)
        lo_grp_logs.setSpacing(8)

        self.chk_stroke_summary = QtWidgets.QCheckBox("Log Sumarizado por Traço no Terminal (1 linha ao soltar a caneta)")
        self.chk_stroke_summary.setChecked(True)
        self.chk_stroke_summary.toggled.connect(self._on_toggle_stroke_summary)

        self.chk_detailed_log = QtWidgets.QCheckBox("Streaming de Telemetria Contínuo no Console (Amostragem Throttled 5Hz)")
        self.chk_detailed_log.setChecked(False)
        self.chk_detailed_log.toggled.connect(self._on_toggle_detailed_log)

        lo_grp_logs.addWidget(self.chk_stroke_summary)
        lo_grp_logs.addWidget(self.chk_detailed_log)
        lo_tools.addWidget(grp_logs)

        grp_bench = QtWidgets.QGroupBox("Testes de Desempenho & Diagnóstico Técnico")
        lo_grp_bench = QtWidgets.QVBoxLayout(grp_bench)
        lo_grp_bench.setSpacing(10)

        lo_btn_row = QtWidgets.QHBoxLayout()
        self.btn_benchmark = QtWidgets.QPushButton("⚡ Executar Benchmark Sintético (1000 Dabs)")
        self.btn_benchmark.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_benchmark.clicked.connect(self._run_benchmark)

        self.btn_copy_report = QtWidgets.QPushButton("📋 Copiar Relatório do Sistema")
        self.btn_copy_report.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_copy_report.clicked.connect(self._copy_diagnostic_report)

        lo_btn_row.addWidget(self.btn_benchmark)
        lo_btn_row.addWidget(self.btn_copy_report)
        lo_grp_bench.addLayout(lo_btn_row)

        self.lbl_bench_result = QtWidgets.QLabel("Status: Aguardando execução do teste.")
        self.lbl_bench_result.setStyleSheet("font-size: 11px; font-style: italic;")
        lo_grp_bench.addWidget(self.lbl_bench_result)
        lo_tools.addWidget(grp_bench)
        lo_tools.addStretch()

        self.tabs.addTab(tab_tools, "⚙️ Logs & Benchmark")

        self.grp_hw = grp_hw
        self.grp_opt = grp_opt
        self.grp_logs = grp_logs
        self.grp_bench = grp_bench

        self.content_layout.addWidget(self.tabs)

        # Botão Fechar no rodapé
        self.btn_close = QtWidgets.QPushButton("Fechar")
        self.btn_close.setFixedWidth(100)
        self.btn_close.clicked.connect(self.accept)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.btn_close)
        self.content_layout.addLayout(btn_row)

    def retranslate_ui(self) -> None:
        from ui.core.i18n import tr
        self.setWindowTitle(tr("telemetry.dialog_title", "Diagnóstico & Telemetria do Motor"))
        if hasattr(self, "title_bar") and self.title_bar:
            self.title_bar.set_title(tr("telemetry.dialog_title", "Diagnóstico & Telemetria do Motor"))

        if hasattr(self, "tabs"):
            self.tabs.setTabText(0, tr("telemetry.tab_performance", "📈 Desempenho"))
            self.tabs.setTabText(1, tr("telemetry.tab_memory", "🧠 Memória & Tiles"))
            self.tabs.setTabText(2, tr("telemetry.tab_pipeline", "🔬 Pipeline & Viewport"))
            self.tabs.setTabText(3, tr("telemetry.tab_pen", "🖊️ Sensor da Caneta"))
            self.tabs.setTabText(4, tr("telemetry.tab_system", "⚙️ Sistema & Logs"))

        if hasattr(self, "card_latency"):
            self.card_latency.set_label(tr("telemetry.card_latency", "Latência do Motor (C++)"))
            self.card_dabs_sec.set_label(tr("telemetry.card_dabs", "Taxa de Carimbos"))
            self.card_stylus_hz.set_label(tr("telemetry.card_stylus_hz", "Frequência da Mesa"))
            self.card_stroke_time.set_label(tr("telemetry.card_stroke_time", "Duração do Traço"))

            self.card_stage_kin.set_label("1. Cinemática / Dinâmica")
            self.card_stage_int.set_label("2. Interpolação Dabs")
            self.card_stage_dab.set_label("3. RasterDab (Shaders)")
            self.card_stage_und.set_label("4. Undo Record (Tiles)")
            self.card_stage_cmp.set_label("5. Compositor Camadas")
            self.card_stage_blt.set_label("6. Apresentação Blit Qt")

            self.card_vp_fps.set_label("Taxa Real da Viewport")
            self.card_vp_dirty.set_label("Região Repintada (Último Blit)")
            self.card_vp_tiles.set_label("Tiles Gravados (Segmento)")
            self.card_vp_dabs.set_label("Dabs Emitidos (Segmento)")

            self.card_tiles_count.set_label(tr("telemetry.card_tiles", "Tiles Alocados (64x64)"))
            self.card_canvas_ram.set_label(tr("telemetry.card_canvas_ram", "RAM do Documento"))
            self.card_undo_ram.set_label(tr("telemetry.card_undo_ram", "RAM do Histórico (Undo)"))
            self.card_undo_steps.set_label(tr("telemetry.card_undo_steps", "Passos de Desfazer"))

            self.card_raw_press.set_label(tr("telemetry.card_raw_press", "Pressão Física"))
            self.card_dyn_press.set_label(tr("telemetry.card_curve_press", "Pressão Curva/Modulada"))
            self.card_velocity.set_label(tr("telemetry.stroke_velocity", "Velocidade do Traço"))
            self.card_lag.set_label(tr("telemetry.card_lag", "Lag do Estabilizador"))

        if hasattr(self, "grp_hw"):
            self.grp_hw.setTitle(tr("telemetry.hw_acceleration", "Aceleração de Hardware & Motor"))
        if hasattr(self, "grp_opt"):
            self.grp_opt.setTitle(tr("telemetry.mem_management", "Gestão & Limpeza de Memória"))
        if hasattr(self, "btn_clear_undo"):
            self.btn_clear_undo.setText(tr("telemetry.clear_undo", "🧹 Limpar Histórico de Desfazer"))
        if hasattr(self, "grp_logs"):
            self.grp_logs.setTitle(tr("telemetry.sys_logs", "Logs do Sistema & Nível de Depuração"))
        if hasattr(self, "grp_bench"):
            self.grp_bench.setTitle(tr("telemetry.bench_group", "Testes de Desempenho & Diagnóstico Técnico"))
        if hasattr(self, "btn_close"):
            self.btn_close.setText(tr("dialogs.close", "Fechar"))

    def _refresh_metrics(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if not backend or not hasattr(backend, "get_telemetry_snapshot"):
            return

        snap: TelemetrySnapshot = backend.get_telemetry_snapshot()
        if snap is None:
            return

        # 1. Desempenho Geral
        self.card_latency.set_value(f"{snap.last_segment_latency_us:.2f} µs")
        self.card_dabs_sec.set_value(f"{snap.total_dabs_per_second:,} dabs/s")
        self.card_stylus_hz.set_value(f"{snap.input_event_rate_hz} Hz")
        self.card_stroke_time.set_value(f"{snap.stroke_total_time_ms:.1f} ms")

        # 2. Pipeline Granular & Viewport
        from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
        vp = RenderWidget.get_active_viewport_telemetry()
        blit_ms = vp.get("qt_draw_image_ms", 0.0)
        vp_fps = vp.get("qt_fps", 0.0)
        dw = int(getattr(snap, "last_dirty_width", 0.0))
        dh = int(getattr(snap, "last_dirty_height", 0.0))
        tiles_rec = getattr(snap, "last_tiles_recorded", 0)
        dabs_rendered = getattr(snap, "last_dabs_rendered", 0)

        self.card_stage_kin.set_value(f"{getattr(snap, 'time_kinematics_us', 0.0):.1f} µs")
        self.card_stage_int.set_value(f"{getattr(snap, 'time_interpolation_us', 0.0):.1f} µs")
        self.card_stage_dab.set_value(f"{getattr(snap, 'time_raster_dab_us', 0.0):.1f} µs")
        self.card_stage_und.set_value(f"{getattr(snap, 'time_undo_record_us', 0.0):.1f} µs")
        self.card_stage_cmp.set_value(f"{getattr(snap, 'time_composite_us', 0.0):.1f} µs")
        self.card_stage_blt.set_value(f"{blit_ms:.2f} ms")

        self.card_vp_fps.set_value(f"{vp_fps:.1f} FPS")
        self.card_vp_dirty.set_value(f"{dw} × {dh} px")
        self.card_vp_tiles.set_value(f"{tiles_rec} tiles")
        self.card_vp_dabs.set_value(f"{dabs_rendered} dabs")

        # 3. Memória & Tiles
        self.card_tiles_count.set_value(f"{snap.active_tile_count}")
        self.card_canvas_ram.set_value(f"{snap.tile_grid_memory_mb:.2f} MB")
        self.card_undo_ram.set_value(f"{snap.undo_stack_memory_mb:.2f} MB")
        self.card_undo_steps.set_value(f"{snap.undo_steps_count}")

        # 4. Sensor & Cinemática
        self.card_raw_press.set_value(f"{int(snap.raw_pressure * 100)} %")
        self.card_dyn_press.set_value(f"{int(snap.dynamic_pressure * 100)} %")
        self.card_velocity.set_value(f"{int(snap.stroke_velocity)} px/s")
        self.card_lag.set_value(f"{snap.stabilizer_lag_px:.1f} px")

        # Atualiza o TelemetryTracker global unificado
        from ui.core.engine.telemetry_tracker import TelemetryTracker
        TelemetryTracker.instance().update(snap, vp)

    def _on_clear_undo(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "_redo_stack") and hasattr(backend, "_action_stack"):
            backend._action_stack.clear()
            backend._redo_stack.clear()
        QtWidgets.QMessageBox.information(self, "Memória", "Pilha de histórico e desfazer limpa com sucesso.")

    def _on_toggle_stroke_summary(self, checked: bool) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_telemetry_enabled"):
            backend.set_telemetry_enabled(checked)

    def _on_toggle_detailed_log(self, checked: bool) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_detailed_logging_enabled"):
            backend.set_detailed_logging_enabled(checked)

    def _run_benchmark(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if not backend or not hasattr(backend, "paint_stroke"):
            self.lbl_bench_result.setText("❌ Motor nativo não disponível para benchmark.")
            return

        self.lbl_bench_result.setText("⏳ Executando teste de estresse de 1.000 dabs...")
        QtWidgets.QApplication.processEvents()

        t0 = time.perf_counter()
        backend.start_stroke(100.0, 100.0, 1.0)
        steps = 1000
        for i in range(steps):
            x = 100.0 + (i % 200)
            y = 100.0 + (i // 5)
            backend.paint_stroke(x, y, 0.8)
        backend.end_stroke(300.0, 300.0)
        dt = (time.perf_counter() - t0) * 1000.0

        dabs_per_sec = int((steps / dt) * 1000.0) if dt > 0 else 0
        self.lbl_bench_result.setText(
            f"✅ Concluído em {dt:.2f} ms | Rendimento: {dabs_per_sec:,} dabs/s ({dt/steps:.3f} ms/dab)"
        )

    def _copy_diagnostic_report(self) -> None:
        """Copia o relatório completo com 20 medidores do Grid e histórico de transições."""
        from ui.core.engine.telemetry_tracker import TelemetryTracker
        report = TelemetryTracker.instance().generate_full_report()
        QtWidgets.QApplication.clipboard().setText(report)
        QtWidgets.QMessageBox.information(
            self,
            "Relatório de Telemetria Copiado",
            "Relatório completo de telemetria (incluindo todos os 20 medidores do Grid, "
            "diagnóstico do pipeline, picos de estresse e histórico de alterações de estado) "
            "foi copiado para a Área de Transferência com sucesso!"
        )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._timer.stop()
        super().closeEvent(event)
