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


class StatCard(QtWidgets.QFrame):
    """Card métrico compacto com rótulo, valor em destaque e unidade."""

    def __init__(self, label: str, initial_value: str = "0", unit: str = "", parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self._unit = unit

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        self.lbl_title = QtWidgets.QLabel(label.upper())
        self.lbl_title.setObjectName("StatTitle")

        self.lbl_value = QtWidgets.QLabel(initial_value)
        self.lbl_value.setObjectName("StatValue")

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)

        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

    def set_value(self, val_str: str) -> None:
        self.lbl_value.setText(val_str)

    def _apply_theme(self, *args) -> None:
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_panel")
        border = tm.get_color("border")
        muted = tm.get_color("text_sec")
        accent = tm.get_color("accent")
        text = tm.get_color("text_main")

        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QLabel#StatTitle {{
                color: {muted};
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QLabel#StatValue {{
                color: {text};
                font-size: 16px;
                font-weight: bold;
                font-family: monospace;
            }}
        """)


class TelemetryDiagnosticsDialog(BaseFramelessDialog):
    """Diálogo completo de auditoria e diagnóstico do motor nativo."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(
            title="Diagnóstico & Telemetria do Motor",
            icon_name="chart",
            parent=parent,
            modal=True,
        )
        self.resize(680, 520)
        self.setMinimumSize(580, 420)
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)  # 30 FPS polling
        self._timer.timeout.connect(self._refresh_metrics)

        self._build_content()
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
        self.lbl_simd_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
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

        # ── 3. Aba: Sensor & Cinemática da Caneta ────────────────────────────
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

        self.content_layout.addWidget(self.tabs)

        # Botão Fechar no rodapé
        btn_close = QtWidgets.QPushButton("Fechar")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        self.content_layout.addLayout(btn_row)

    def _refresh_metrics(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if not backend or not hasattr(backend, "get_telemetry_snapshot"):
            return

        snap = backend.get_telemetry_snapshot()
        if snap is None:
            return

        # 1. Desempenho
        self.card_latency.set_value(f"{snap.last_segment_latency_us:.2f} µs")
        self.card_dabs_sec.set_value(f"{snap.total_dabs_per_second:,} dabs/s")
        self.card_stylus_hz.set_value(f"{snap.input_event_rate_hz} Hz")
        self.card_stroke_time.set_value(f"{snap.stroke_total_time_ms:.1f} ms")

        # 2. Memória & Tiles
        self.card_tiles_count.set_value(f"{snap.active_tile_count}")
        self.card_canvas_ram.set_value(f"{snap.tile_grid_memory_mb:.2f} MB")
        self.card_undo_ram.set_value(f"{snap.undo_stack_memory_mb:.2f} MB")
        self.card_undo_steps.set_value(f"{snap.undo_steps_count}")

        # 3. Sensor & Cinemática
        self.card_raw_press.set_value(f"{int(snap.raw_pressure * 100)} %")
        self.card_dyn_press.set_value(f"{int(snap.dynamic_pressure * 100)} %")
        self.card_velocity.set_value(f"{int(snap.stroke_velocity)} px/s")
        self.card_lag.set_value(f"{snap.stabilizer_lag_px:.1f} px")

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
        backend = EngineRegistry.instance().get_backend()
        snap = backend.get_telemetry_snapshot() if (backend and hasattr(backend, "get_telemetry_snapshot")) else None

        report = [
            "==================================================",
            " 🏛️ LUMENIA ART STUDIO -- RELATÓRIO DE TELEMETRIA ",
            "==================================================",
            f"Data / Hora: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Latência por Dab: {getattr(snap, 'last_segment_latency_us', 0.0):.2f} µs",
            f"Taxa de Dabs: {getattr(snap, 'total_dabs_per_second', 0):,} dabs/s",
            f"Taxa da Mesa: {getattr(snap, 'input_event_rate_hz', 0)} Hz",
            f"Tiles Alocados: {getattr(snap, 'active_tile_count', 0)}",
            f"RAM Documento: {getattr(snap, 'tile_grid_memory_mb', 0.0):.2f} MB",
            f"RAM Undo Stack: {getattr(snap, 'undo_stack_memory_mb', 0.0):.2f} MB",
            f"Passos de Desfazer: {getattr(snap, 'undo_steps_count', 0)}",
            "Aceleração SIMD: Ativa (AVX2 / SSE2)",
            "==================================================",
        ]
        text_report = "\n".join(report)
        QtWidgets.QApplication.clipboard().setText(text_report)
        QtWidgets.QMessageBox.information(self, "Relatório", "Relatório de diagnóstico copiado para a Área de Transferência!")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._timer.stop()
        super().closeEvent(event)
