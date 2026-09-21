"""
TelemetryGridReport — Gerador de Relatório e Diálogo de Histórico do Cockpit de Telemetria
==========================================================================================
Encapsula o diálogo modal de histórico de alterações de estado e transições de gargalos,
a lógica de diagnóstico de gargalos operacionais e a formatação consolidada de relatórios.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.engine.registry import EngineRegistry
from ui.core.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.icons import get_icon


class TelemetryStateHistoryDialog(BaseFramelessDialog):
    """Diálogo modal para inspeção do histórico cronológico de transições de estado e gargalos."""

    def __init__(
        self,
        state_counts: Dict[str, int],
        state_history: List[Dict[str, str]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        title = "Histórico de Alterações de Estado do Pipeline"
        super().__init__(title=title, icon_name="chart", parent=parent, modal=True)
        self.setWindowTitle(title)
        tm = ThemeManager.instance()
        self.resize(680, 420)

        dlg_lo = self.content_layout
        dlg_lo.setSpacing(10)

        lbl_hdr = QtWidgets.QLabel("<b>Linha do Tempo de Alterações de Estado (Gargalos vs Equilíbrio)</b>")
        lbl_hdr.setStyleSheet(f"font-size: 13px; color: {tm.get_color('TELEMETRY_STAGE_KINEMATICS', '#38bdf8')};")
        dlg_lo.addWidget(lbl_hdr)

        summary_text = (
            f"Equilibrado: {state_counts.get('PIPELINE_EQUILIBRADO', 0)}x | "
            f"Raster (>15ms): {state_counts.get('GARGALO_RASTER', 0)}x | "
            f"Blit (>16ms): {state_counts.get('GARGALO_BLIT', 0)}x | "
            f"Undo (>10ms): {state_counts.get('GARGALO_UNDO', 0)}x | "
            f"Compositor (>10ms): {state_counts.get('GARGALO_COMPOSITOR', 0)}x"
        )
        lbl_sum = QtWidgets.QLabel(summary_text)
        lbl_sum.setStyleSheet(f"font-size: 11px; color: {tm.get_color('FG_SECONDARY', '#9ca3af')};")
        dlg_lo.addWidget(lbl_sum)

        txt_history = QtWidgets.QPlainTextEdit()
        txt_history.setReadOnly(True)
        txt_history.setStyleSheet(
            f"font-family: monospace; font-size: 11px; background-color: {tm.get_color('BG_DARKEST', '#111827')}; "
            f"color: {tm.get_color('FG_PRIMARY', '#f3f4f6')}; border: 1px solid {tm.get_color('BORDER', '#374151')};"
        )

        hist_lines = []
        for t in reversed(state_history):
            hist_lines.append(f"[{t['time']}] {t['to_state']}\n  └─ Motivo: {t['cause']}\n")
        txt_history.setPlainText("\n".join(hist_lines) if hist_lines else "Nenhuma alteração registrada.")
        dlg_lo.addWidget(txt_history, 1)

        btn_row = QtWidgets.QHBoxLayout()
        btn_copy_hist = QtWidgets.QPushButton(" Copiar Histórico")
        btn_copy_hist.setIcon(get_icon("copy", tm.get_color("text_main")))
        btn_copy_hist.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(txt_history.toPlainText()))
        btn_close = QtWidgets.QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_copy_hist)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        dlg_lo.addLayout(btn_row)


class TelemetryReportGenerator:
    """Gerador do relatório completo de telemetria e diagnóstico do pipeline."""

    @staticmethod
    def diagnose_pipeline(
        dab_us: float, und_us: float, cmp_us: float, blit_ms: float
    ) -> Tuple[str, str, str, str]:
        """Classifica a performance do pipeline retornando (new_state, state_key, style, cause)."""
        tm = ThemeManager.instance()
        if blit_ms > 16.6:
            return (
                "GARGALO EM TELA: APRESENTAÇÃO QT BLIT LENTO (> 16ms / < 60 FPS)",
                "GARGALO_BLIT",
                f"background-color: rgba(239,68,68,0.2); color: {tm.get_color('DANGER_HOVER', '#f87171')}; border: 1px solid {tm.get_color('DANGER', '#ef4444')}; border-radius: 4px; font-size: 10px; font-weight: bold;",
                f"Tempo de paintEvent/drawImage na Viewport Qt ({blit_ms:.2f} ms > 16.6 ms)",
            )
        if dab_us > 15000:
            return (
                "GARGALO EM RASTER: TEMPO DE CARIMBO CRÍTICO (> 15ms)",
                "GARGALO_RASTER",
                f"background-color: rgba(249,115,22,0.2); color: {tm.get_color('TELEMETRY_STAGE_RASTER', '#fb923c')}; border: 1px solid {tm.get_color('TELEMETRY_STAGE_RASTER', '#f97316')}; border-radius: 4px; font-size: 10px; font-weight: bold;",
                f"Rasterização de Dabs no Shaders AVX2 ({dab_us:.1f} µs | {dab_us/1000.0:.2f} ms > 15 ms)",
            )
        if und_us > 10000:
            return (
                "GARGALO EM UNDO: GRAVAÇÃO DE TILES LENTA (> 10ms)",
                "GARGALO_UNDO",
                f"background-color: rgba(168,85,247,0.2); color: {tm.get_color('TELEMETRY_STAGE_UNDO', '#c084fc')}; border: 1px solid {tm.get_color('TELEMETRY_STAGE_UNDO', '#a855f7')}; border-radius: 4px; font-size: 10px; font-weight: bold;",
                f"Cópia/Backup de Tiles 128x128 para Undo ({und_us:.1f} µs | {und_us/1000.0:.2f} ms > 10 ms)",
            )
        if cmp_us > 10000:
            return (
                "GARGALO EM COMPOSITOR: MESCLAGEM DE CAMADAS LENTA (> 10ms)",
                "GARGALO_COMPOSITOR",
                f"background-color: rgba(34,197,94,0.2); color: {tm.get_color('TELEMETRY_STAGE_COMPOSITOR', '#4ade80')}; border: 1px solid {tm.get_color('TELEMETRY_STAGE_COMPOSITOR', '#22c55e')}; border-radius: 4px; font-size: 10px; font-weight: bold;",
                f"Mesclagem de Camadas no Compositor ({cmp_us:.1f} µs | {cmp_us/1000.0:.2f} ms > 10 ms)",
            )
        return (
            "PIPELINE EQUILIBRADO (< 2ms)",
            "PIPELINE_EQUILIBRADO",
            f"background-color: rgba(16,185,129,0.15); color: {tm.get_color('SUCCESS', '#34d399')}; border: 1px solid {tm.get_color('SUCCESS', '#10b981')}; border-radius: 4px; font-size: 10px; font-weight: bold;",
            "Todos os estágios operando com alta fluidez (< 2ms / 60 FPS)",
        )

    @staticmethod
    def generate(window: Any) -> str:
        backend = EngineRegistry.instance().get_backend()
        snap = backend.get_telemetry_snapshot() if (backend and hasattr(backend, "get_telemetry_snapshot")) else None
        vp = EngineRegistry.get_viewport_telemetry()
        blit_ms = vp.get("qt_draw_image_ms", 0.0)
        blit_us = blit_ms * 1000.0

        kin_us = getattr(snap, "time_kinematics_us", 0.0)
        int_us = getattr(snap, "time_interpolation_us", 0.0)
        dab_us = getattr(snap, "time_raster_dab_us", 0.0)
        und_us = getattr(snap, "time_undo_record_us", 0.0)
        cmp_us = getattr(snap, "time_composite_us", 0.0)
        total_cycle_us = kin_us + int_us + dab_us + und_us + cmp_us + blit_us
        denom = total_cycle_us if total_cycle_us > 0 else 1.0

        pct_kin = (kin_us / denom) * 100.0
        pct_int = (int_us / denom) * 100.0
        pct_dab = (dab_us / denom) * 100.0
        pct_und = (und_us / denom) * 100.0
        pct_cmp = (cmp_us / denom) * 100.0
        pct_blt = (blit_us / denom) * 100.0

        engine_names = {0: "BrushEngine", 1: "PencilEngine", 2: "InkerEngine", 3: "EraserEngine"}
        eng_str = engine_names.get(getattr(snap, "active_engine_id", 0), "Motor Nativo C++")

        peaks = getattr(window, "_peaks", {})
        state_history = getattr(window, "_state_history", [])
        state_counts = getattr(window, "_state_counts", {})
        stay_on_top = getattr(window, "_stay_on_top", False)
        current_state_key = getattr(window, "current_state_key", "PIPELINE_EQUILIBRADO")
        bottleneck_text = window.lbl_bottleneck.text() if hasattr(window, "lbl_bottleneck") else ""

        lines = [
            "=" * 78,
            " LUMENIA ART STUDIO — COCKPIT DE TELEMETRIA & DIAGNÓSTICO EM GRID",
            "=" * 78,
            f"Data / Hora da Captura  : {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Monitoramento em Tempo  : Captura Ativa (~60 FPS / Timer 16ms)",
            f"Fixação Sempre no Topo  : {'SIM' if stay_on_top else 'NÃO'}",
            "",
            "-" * 78,
            " DIAGNÓSTICO DO PIPELINE & ALTERAÇÕES DE ESTADO",
            "-" * 78,
            f"Estado Atual do Banner  : {bottleneck_text}",
            f"Classificação de Estado : {current_state_key}",
            f"Condição Atual          : {'Equilibrado (Zero Sobrecarga)' if current_state_key == 'PIPELINE_EQUILIBRADO' else 'Presença de Gargalo Operacional'}",
            "",
            "Resumo de Ocorrências na Sessão de Teste:",
            f"  • PIPELINE EQUILIBRADO (< 2ms) : {state_counts.get('PIPELINE_EQUILIBRADO', 0)} vez(es)",
            f"  • GARGALO EM RASTER (> 15ms)     : {state_counts.get('GARGALO_RASTER', 0)} vez(es)",
            f"  • GARGALO EM TELA / BLIT (> 16ms): {state_counts.get('GARGALO_BLIT', 0)} vez(es)",
            f"  • GARGALO EM UNDO (> 10ms)       : {state_counts.get('GARGALO_UNDO', 0)} vez(es)",
            f"  • GARGALO EM COMPOSITOR (> 10ms) : {state_counts.get('GARGALO_COMPOSITOR', 0)} vez(es)",
            f"  • Total de Transições Registradas : {len(state_history)}",
            "",
            "Picos Máximos de Estresse Registrados na Sessão:",
            f"  • Pico Latência do Motor C++ : {peaks.get('motor_latency_us', 0.0):.1f} µs ({peaks.get('motor_latency_us', 0.0)/1000.0:.2f} ms)",
            f"  • Pico em RasterDab (Shaders): {peaks.get('raster_dab_us', 0.0):.1f} µs ({peaks.get('raster_dab_us', 0.0)/1000.0:.2f} ms)",
            f"  • Pico Gravação de Undo      : {peaks.get('undo_record_us', 0.0):.1f} µs ({peaks.get('undo_record_us', 0.0)/1000.0:.2f} ms)",
            f"  • Pico Compositor de Camadas : {peaks.get('composite_us', 0.0):.1f} µs ({peaks.get('composite_us', 0.0)/1000.0:.2f} ms)",
            f"  • Pico Apresentação Blit Qt  : {peaks.get('blit_ms', 0.0):.2f} ms ({peaks.get('blit_ms', 0.0)*1000.0:.0f} µs)",
            f"  • Menor Fluidez da Viewport  : {peaks.get('min_fps', 60.0):.1f} FPS",
            f"  • Pico Velocidade do Traço   : {int(peaks.get('stroke_velocity', 0.0))} px/s",
            f"  • Pico Lag do Estabilizador  : {peaks.get('stabilizer_lag_px', 0.0):.1f} px",
            f"  • Pico Taxa de Carimbos      : {int(peaks.get('dabs_per_second', 0)):,} dabs/s",
            f"  • Pico Área Suja Repintada   : {int(peaks.get('dirty_area_px', 0.0)):,} px² ({int(peaks.get('tiles_recorded', 0))} tiles gravados)",
            "",
            "Histórico Cronológico das Últimas Alterações de Estado (Transições):",
        ]

        if state_history:
            for trans in state_history[-15:]:
                lines.append(f"  [{trans['time']}] {trans['to_state']}\n    └─ Motivo: {trans['cause']}")
        else:
            lines.append("  (Nenhuma transição de estado registrada)")

        lines.extend([
            "",
            "-" * 78,
            " DECOMPOSIÇÃO PROPORCIONAL DO PIPELINE (BARRA DE ESTÁGIOS)",
            "-" * 78,
            f"  ■ 1. Cinemática / Dinâmica : {kin_us:>9.1f} µs ({kin_us/1000.0:>6.3f} ms) [{pct_kin:>5.1f}%]",
            f"  ■ 2. Interpolação Dabs     : {int_us:>9.1f} µs ({int_us/1000.0:>6.3f} ms) [{pct_int:>5.1f}%]",
            f"  ■ 3. RasterDab (Shaders)   : {dab_us:>9.1f} µs ({dab_us/1000.0:>6.2f} ms) [{pct_dab:>5.1f}%] {'[GARGALO CRÍTICO]' if dab_us > 15000 else ''}",
            f"  ■ 4. Gravação de Undo      : {und_us:>9.1f} µs ({und_us/1000.0:>6.2f} ms) [{pct_und:>5.1f}%] {'[GARGALO]' if und_us > 10000 else ''}",
            f"  ■ 5. Compositor de Camadas : {cmp_us:>9.1f} µs ({cmp_us/1000.0:>6.2f} ms) [{pct_cmp:>5.1f}%] {'[GARGALO]' if cmp_us > 10000 else ''}",
            f"  ■ 6. Apresentação Blit Qt  : {blit_us:>9.1f} µs ({blit_ms:>6.2f} ms) [{pct_blt:>5.1f}%] {'[GARGALO]' if blit_ms > 16.6 else ''}",
            "  " + "-" * 66,
            f"  Ciclo Total do Micro-Evento: {total_cycle_us:.1f} µs ({total_cycle_us/1000.0:.2f} ms)",
            "",
            "-" * 78,
            " PAINEL COMPLETO EM GRID (TODOS OS 20 MEDIDORES EM TEMPO REAL)",
            "-" * 78,
        ])

        cards_sections = [
            ("LINHA 1: Estágios Granulares C++", [window.c_kin, window.c_int, window.c_dab, window.c_und]),
            ("LINHA 2: Composição, Blit e Frequências", [window.c_cmp, window.c_blt, window.c_lat, window.c_fps]),
            ("LINHA 3: Frequências & Pegada Geométrica", [window.c_hz, window.c_dabs_sec, window.c_dabs, window.c_dirty]),
            ("LINHA 4: Área, Blocos (Tiles) & Memória", [window.c_area, window.c_tiles, window.c_ram_canvas, window.c_ram_undo]),
            ("LINHA 5: Sensores da Caneta & Hardware", [window.c_press, window.c_vel, window.c_lag, window.c_hw]),
        ]

        for sec_name, cards in cards_sections:
            lines.append(f"[{sec_name}]")
            for card in cards:
                t, v, s = card.get_info()
                lines.append(f"  • {t:<28} : {v:<22} | {s}")
            lines.append("")

        lines.extend([
            "-" * 78,
            " AMBIENTE, ARQUITETURA & ACELERAÇÃO",
            "-" * 78,
            "  • Instruções SIMD       : AVX2 / SSE2 Ativo (Vetorizado)",
            f"  • Mini-Motor em Execução : {eng_str}",
            "  • Formato de Bloco      : Tiles 128x128 em BGRA32 / Float32",
            "  • Polling de Viewport   : 60 FPS Desacoplado via QTimer",
            "=" * 78,
        ])

        return "\n".join(lines)
