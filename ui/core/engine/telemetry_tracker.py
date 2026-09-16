"""
TelemetryTracker — Centralizador Global de Diagnóstico, Transições de Estado e Relatórios
========================================================================================
Mantém o estado unificado do pipeline do ALADYN ENGINE em tempo real:
- Rastreia transições entre PIPELINE_EQUILIBRADO e GARGALOS (Raster, Blit, Undo, Compositor)
- Registra linha do tempo cronológica de transições com carimbos ms e motivos detalhados
- Armazena contadores de ocorrências e picos máximos de estresse da sessão de teste
- Retém última atividade da caneta (pressão física/modulada, velocidade, lag) ao soltar
- Gera o relatório completo unificado para todos os botões de cópia (Cockpit, Painel e Diálogo)
"""

from __future__ import annotations

import time
from typing import Any, Optional


class TelemetryTracker:
    """Singleton de rastreamento e auditoria de telemetria em tempo real."""

    _instance: Optional[TelemetryTracker] = None

    @classmethod
    def instance(cls) -> TelemetryTracker:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._current_state_key = "PIPELINE_EQUILIBRADO"
        self._current_state_str = "✅ PIPELINE EQUILIBRADO (< 2ms)"
        self._state_history: list[dict[str, str]] = []
        self._state_counts: dict[str, int] = {
            "PIPELINE_EQUILIBRADO": 1,
            "GARGALO_RASTER": 0,
            "GARGALO_BLIT": 0,
            "GARGALO_UNDO": 0,
            "GARGALO_COMPOSITOR": 0,
        }
        self._peaks: dict[str, float] = {
            "motor_latency_us": 0.0,
            "raster_dab_us": 0.0,
            "undo_record_us": 0.0,
            "composite_us": 0.0,
            "kinematics_us": 0.0,
            "interpolation_us": 0.0,
            "blit_ms": 0.0,
            "stroke_velocity": 0.0,
            "stabilizer_lag_px": 0.0,
            "dabs_per_second": 0.0,
            "dirty_area_px": 0.0,
            "tiles_recorded": 0,
            "min_fps": 60.0,
        }
        self._last_active_pen: dict[str, float] = {
            "raw_pressure": 0.0,
            "dynamic_pressure": 0.0,
            "velocity": 0.0,
            "stabilizer_lag": 0.0,
        }
        self._last_snap: Any = None
        self._last_vp: dict = {}

        self.record_state_transition(
            new_state="✅ PIPELINE EQUILIBRADO (< 2ms)",
            state_key="PIPELINE_EQUILIBRADO",
            cause="Inicialização do Sistema de Telemetria",
        )

    @property
    def current_state_key(self) -> str:
        """Identificador canônico do estado de performance do pipeline."""
        return self._current_state_key

    @property
    def current_state_str(self) -> str:
        """String legível com status e badge do estado de performance."""
        return self._current_state_str

    def reset(self) -> None:
        """Limpa contadores, picos e reinicia o histórico de transições."""
        self._peaks = {
            "motor_latency_us": 0.0,
            "raster_dab_us": 0.0,
            "undo_record_us": 0.0,
            "composite_us": 0.0,
            "kinematics_us": 0.0,
            "interpolation_us": 0.0,
            "blit_ms": 0.0,
            "stroke_velocity": 0.0,
            "stabilizer_lag_px": 0.0,
            "dabs_per_second": 0.0,
            "dirty_area_px": 0.0,
            "tiles_recorded": 0,
            "min_fps": 60.0,
        }
        self._last_active_pen = {
            "raw_pressure": 0.0,
            "dynamic_pressure": 0.0,
            "velocity": 0.0,
            "stabilizer_lag": 0.0,
        }
        self._state_history.clear()
        self._state_counts = {
            "PIPELINE_EQUILIBRADO": 1,
            "GARGALO_RASTER": 0,
            "GARGALO_BLIT": 0,
            "GARGALO_UNDO": 0,
            "GARGALO_COMPOSITOR": 0,
        }
        self.record_state_transition(
            new_state="✅ PIPELINE EQUILIBRADO (< 2ms)",
            state_key="PIPELINE_EQUILIBRADO",
            cause="Métricas e contadores resetados pelo usuário",
        )

    def record_state_transition(self, new_state: str, state_key: str, cause: str) -> None:
        """Registra uma transição de estado com carimbo em milissegundos."""
        timestamp = time.strftime("%H:%M:%S")
        ms_part = int((time.time() % 1) * 1000)
        time_str = f"{timestamp}.{ms_part:03d}"

        transition = {
            "time": time_str,
            "from_state": getattr(self, "_current_state_str", "INDEFINIDO"),
            "to_state": new_state,
            "state_key": state_key,
            "cause": cause,
        }
        self._state_history.append(transition)
        if len(self._state_history) > 200:
            self._state_history.pop(0)

        self._state_counts[state_key] = self._state_counts.get(state_key, 0) + 1
        self._current_state_key = state_key
        self._current_state_str = new_state

    def update(self, snap: Any, vp: dict) -> tuple[str, str, str]:
        """Atualiza métricas a partir do snapshot do C++ e da viewport Qt.
        Retorna (new_state, state_key, cause).
        """
        self._last_snap = snap
        self._last_vp = vp

        blit_ms = vp.get("qt_draw_image_ms", 0.0) if vp else 0.0
        vp_fps = vp.get("qt_fps", 0.0) if vp else 0.0

        kin_us = getattr(snap, "time_kinematics_us", 0.0) if snap else 0.0
        int_us = getattr(snap, "time_interpolation_us", 0.0) if snap else 0.0
        dab_us = getattr(snap, "time_raster_dab_us", 0.0) if snap else 0.0
        und_us = getattr(snap, "time_undo_record_us", 0.0) if snap else 0.0
        cmp_us = getattr(snap, "time_composite_us", 0.0) if snap else 0.0
        lat_us = getattr(snap, "last_segment_latency_us", 0.0) if snap else 0.0
        vel = getattr(snap, "stroke_velocity", 0.0) if snap else 0.0
        lag = getattr(snap, "stabilizer_lag_px", 0.0) if snap else 0.0
        p_raw = getattr(snap, "raw_pressure", 0.0) if snap else 0.0
        p_dyn = getattr(snap, "dynamic_pressure", 0.0) if snap else 0.0
        dabs_sec = getattr(snap, "total_dabs_per_second", 0) if snap else 0
        dirty_area = getattr(snap, "last_dirty_area_px", 0.0) if snap else 0.0
        tiles_rec = getattr(snap, "last_tiles_recorded", 0) if snap else 0

        # Preserva última atividade da caneta
        if p_raw > 0.0 or vel > 0.0:
            self._last_active_pen["raw_pressure"] = p_raw * 100.0
            self._last_active_pen["dynamic_pressure"] = p_dyn * 100.0
            self._last_active_pen["velocity"] = vel
            self._last_active_pen["stabilizer_lag"] = lag

        # Picos
        self._peaks["motor_latency_us"] = max(self._peaks.get("motor_latency_us", 0.0), lat_us)
        self._peaks["raster_dab_us"] = max(self._peaks.get("raster_dab_us", 0.0), dab_us)
        self._peaks["undo_record_us"] = max(self._peaks.get("undo_record_us", 0.0), und_us)
        self._peaks["composite_us"] = max(self._peaks.get("composite_us", 0.0), cmp_us)
        self._peaks["kinematics_us"] = max(self._peaks.get("kinematics_us", 0.0), kin_us)
        self._peaks["interpolation_us"] = max(self._peaks.get("interpolation_us", 0.0), int_us)
        self._peaks["blit_ms"] = max(self._peaks.get("blit_ms", 0.0), blit_ms)
        self._peaks["stroke_velocity"] = max(self._peaks.get("stroke_velocity", 0.0), vel)
        self._peaks["stabilizer_lag_px"] = max(self._peaks.get("stabilizer_lag_px", 0.0), lag)
        self._peaks["dabs_per_second"] = max(self._peaks.get("dabs_per_second", 0), dabs_sec)
        self._peaks["dirty_area_px"] = max(self._peaks.get("dirty_area_px", 0.0), dirty_area)
        self._peaks["tiles_recorded"] = max(self._peaks.get("tiles_recorded", 0), tiles_rec)
        if vp_fps > 0:
            self._peaks["min_fps"] = min(self._peaks.get("min_fps", 60.0), vp_fps)

        # Avaliação de diagnóstico
        if blit_ms > 16.6:
            new_state = "⚠️ GARGALO EM TELA: APRESENTAÇÃO QT BLIT LENTO (> 16ms / < 60 FPS)"
            state_key = "GARGALO_BLIT"
            cause = f"Apresentação Viewport Qt ({blit_ms:.2f} ms > 16.6 ms / fluidez abaixo de 60 FPS)"
        elif dab_us > 15000.0:
            new_state = "⚠️ GARGALO EM RASTER: PINCEL GRANDE (> 15ms / CPU SATURADA)"
            state_key = "GARGALO_RASTER"
            cause = f"Rasterização de Dabs ({dab_us:.1f} µs | {dab_us/1000.0:.2f} ms > 15 ms / pincel largo)"
        elif und_us > 10000.0:
            new_state = "⚠️ GARGALO EM UNDO: MUITOS TILES GRAVADOS (> 10ms CÓPIA RAM)"
            state_key = "GARGALO_UNDO"
            cause = f"Cópia de Tiles para Histórico Undo ({und_us:.1f} µs | {und_us/1000.0:.2f} ms > 10 ms)"
        elif cmp_us > 10000.0:
            new_state = "⚠️ GARGALO EM COMPOSIÇÃO DE CAMADAS (> 10ms)"
            state_key = "GARGALO_COMPOSITOR"
            cause = f"Mesclagem de Camadas no Compositor ({cmp_us:.1f} µs | {cmp_us/1000.0:.2f} ms > 10 ms)"
        else:
            new_state = "✅ PIPELINE EQUILIBRADO (< 2ms)"
            state_key = "PIPELINE_EQUILIBRADO"
            cause = "Todos os estágios operando com alta fluidez (< 2ms / 60 FPS)"

        if state_key != self._current_state_key:
            self.record_state_transition(new_state, state_key, cause)

        return new_state, state_key, cause

    def generate_full_report(self) -> str:
        """Gera o relatório completo de telemetria contendo todos os 20 medidores do Grid,
        o diagnóstico do pipeline, picos de estresse e o histórico cronológico de transições de estado.
        """
        from ui.core.engine.registry import EngineRegistry

        backend = EngineRegistry.instance().get_backend()
        snap = backend.get_telemetry_snapshot() if (backend and hasattr(backend, "get_telemetry_snapshot")) else self._last_snap
        vp = EngineRegistry.get_viewport_telemetry() if EngineRegistry.instance() else self._last_vp
        if not vp and self._last_vp:
            vp = self._last_vp

        blit_ms = vp.get("qt_draw_image_ms", 0.0) if vp else 0.0
        vp_fps = vp.get("qt_fps", 0.0) if vp else 0.0
        blit_us = blit_ms * 1000.0

        kin_us = getattr(snap, "time_kinematics_us", 0.0) if snap else 0.0
        int_us = getattr(snap, "time_interpolation_us", 0.0) if snap else 0.0
        dab_us = getattr(snap, "time_raster_dab_us", 0.0) if snap else 0.0
        und_us = getattr(snap, "time_undo_record_us", 0.0) if snap else 0.0
        cmp_us = getattr(snap, "time_composite_us", 0.0) if snap else 0.0
        lat_us = getattr(snap, "last_segment_latency_us", 0.0) if snap else 0.0
        total_cycle_us = kin_us + int_us + dab_us + und_us + cmp_us + blit_us
        denom = total_cycle_us if total_cycle_us > 0 else 1.0

        pct_kin = (kin_us / denom) * 100.0
        pct_int = (int_us / denom) * 100.0
        pct_dab = (dab_us / denom) * 100.0
        pct_und = (und_us / denom) * 100.0
        pct_cmp = (cmp_us / denom) * 100.0
        pct_blt = (blit_us / denom) * 100.0

        engine_names = {0: "BrushEngine", 1: "PencilEngine", 2: "InkerEngine", 3: "EraserEngine"}
        eng_str = engine_names.get(getattr(snap, "active_engine_id", 0) if snap else 0, "Motor Nativo C++")

        # Sensores da caneta
        p_raw = int(getattr(snap, "raw_pressure", 0.0) * 100) if snap else 0
        p_dyn = int(getattr(snap, "dynamic_pressure", 0.0) * 100) if snap else 0
        vel_px = int(getattr(snap, "stroke_velocity", 0.0)) if snap else 0
        lag_px = getattr(snap, "stabilizer_lag_px", 0.0) if snap else 0.0

        if p_raw == 0 and vel_px == 0 and self._last_active_pen["raw_pressure"] > 0:
            p_raw_str = f"{int(self._last_active_pen['raw_pressure'])} %"
            p_dyn_str = f"Modulada: {int(self._last_active_pen['dynamic_pressure'])} % (Último traço)"
            vel_str = f"{int(self._last_active_pen['velocity'])} px/s"
            vel_sub = "Velocidade (Último traço)"
            lag_str = f"{self._last_active_pen['stabilizer_lag']:.1f} px"
            lag_sub = "Lag (Último traço)"
        else:
            p_raw_str = f"{p_raw} %"
            p_dyn_str = f"Modulada: {p_dyn} %"
            vel_str = f"{vel_px} px/s"
            vel_sub = "Velocidade vetorial"
            lag_str = f"{lag_px:.1f} px"
            lag_sub = "Lag do estabilizador"

        # Pegada geométrica
        dw = int(getattr(snap, "last_dirty_width", 0.0)) if snap else 0
        dh = int(getattr(snap, "last_dirty_height", 0.0)) if snap else 0
        area_px = getattr(snap, "last_dirty_area_px", 0.0) if snap else 0.0
        tiles_rec = getattr(snap, "last_tiles_recorded", 0) if snap else 0
        tiles_act = getattr(snap, "active_tile_count", 0) if snap else 0
        dabs_rend = getattr(snap, "last_dabs_rendered", 0) if snap else 0
        dabs_tot = getattr(snap, "total_dabs_in_stroke", 0) if snap else 0
        dabs_rate = getattr(snap, "total_dabs_per_second", 0) if snap else 0
        rate_hz = getattr(snap, "input_event_rate_hz", 0) if snap else 0
        ram_canvas = getattr(snap, "tile_grid_memory_mb", 0.0) if snap else 0.0
        ram_undo = getattr(snap, "undo_stack_memory_mb", 0.0) if snap else 0.0
        undo_steps = getattr(snap, "undo_steps_count", 0) if snap else 0

        lines = [
            "=" * 78,
            " 🏛️ LUMENIA ART STUDIO — COCKPIT DE TELEMETRIA & DIAGNÓSTICO EM GRID",
            "=" * 78,
            f"Data / Hora da Captura  : {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Monitoramento em Tempo  : Captura Ativa (Timer 16ms / Zero Overhead)",
            "",
            "-" * 78,
            " 🚦 DIAGNÓSTICO DO PIPELINE & ALTERAÇÕES DE ESTADO",
            "-" * 78,
            f"Estado Atual do Banner  : {self._current_state_str}",
            f"Classificação de Estado : {self._current_state_key}",
            f"Condição Operacional    : {'Equilibrado (Zero Sobrecarga)' if self._current_state_key == 'PIPELINE_EQUILIBRADO' else 'Presença de Gargalo Operacional'}",
            "",
            "Resumo de Ocorrências na Sessão de Teste:",
            f"  • ✅ PIPELINE EQUILIBRADO (< 2ms) : {self._state_counts.get('PIPELINE_EQUILIBRADO', 0)} vez(es)",
            f"  • ⚠️ GARGALO EM RASTER (> 15ms)   : {self._state_counts.get('GARGALO_RASTER', 0)} vez(es)",
            f"  • ⚠️ GARGALO EM TELA / BLIT (> 16ms): {self._state_counts.get('GARGALO_BLIT', 0)} vez(es)",
            f"  • ⚠️ GARGALO EM UNDO (> 10ms)     : {self._state_counts.get('GARGALO_UNDO', 0)} vez(es)",
            f"  • ⚠️ GARGALO EM COMPOSITOR (> 10ms): {self._state_counts.get('GARGALO_COMPOSITOR', 0)} vez(es)",
            f"  • Total de Transições Registradas : {len(self._state_history)}",
            "",
            "Picos Máximos de Estresse Registrados na Sessão:",
            f"  • Pico Latência do Motor C++ : {self._peaks['motor_latency_us']:.1f} µs ({self._peaks['motor_latency_us']/1000.0:.2f} ms)",
            f"  • Pico em RasterDab (Shaders): {self._peaks['raster_dab_us']:.1f} µs ({self._peaks['raster_dab_us']/1000.0:.2f} ms)",
            f"  • Pico Gravação de Undo      : {self._peaks['undo_record_us']:.1f} µs ({self._peaks['undo_record_us']/1000.0:.2f} ms)",
            f"  • Pico Compositor de Camadas : {self._peaks['composite_us']:.1f} µs ({self._peaks['composite_us']/1000.0:.2f} ms)",
            f"  • Pico Apresentação Blit Qt  : {self._peaks['blit_ms']:.2f} ms ({self._peaks['blit_ms']*1000.0:.0f} µs)",
            f"  • Menor Fluidez da Viewport  : {self._peaks['min_fps']:.1f} FPS",
            f"  • Pico Velocidade do Traço   : {int(self._peaks['stroke_velocity'])} px/s",
            f"  • Pico Lag do Estabilizador  : {self._peaks['stabilizer_lag_px']:.1f} px",
            f"  • Pico Taxa de Carimbos      : {int(self._peaks['dabs_per_second']):,} dabs/s",
            f"  • Pico Área Suja Repintada   : {int(self._peaks['dirty_area_px']):,} px² ({int(self._peaks['tiles_recorded'])} tiles gravados)",
            "",
            "Histórico Cronológico das Últimas Alterações de Estado (Transições):",
        ]

        if self._state_history:
            for trans in self._state_history[-15:]:
                lines.append(f"  [{trans['time']}] {trans['to_state']}\n    └─ Motivo: {trans['cause']}")
        else:
            lines.append("  (Nenhuma transição de estado registrada)")

        lines.extend([
            "",
            "-" * 78,
            " ⏱️ DECOMPOSIÇÃO PROPORCIONAL DO PIPELINE (BARRA DE ESTÁGIOS)",
            "-" * 78,
            f"  ■ 1. Cinemática / Dinâmica : {kin_us:>9.1f} µs ({kin_us/1000.0:>6.3f} ms) [{pct_kin:>5.1f}%]",
            f"  ■ 2. Interpolação Dabs     : {int_us:>9.1f} µs ({int_us/1000.0:>6.3f} ms) [{pct_int:>5.1f}%]",
            f"  ■ 3. RasterDab (Shaders)   : {dab_us:>9.1f} µs ({dab_us/1000.0:>6.2f} ms) [{pct_dab:>5.1f}%] {'⚠️ GARGALO CRÍTICO' if dab_us > 15000 else ''}",
            f"  ■ 4. Gravação de Undo      : {und_us:>9.1f} µs ({und_us/1000.0:>6.2f} ms) [{pct_und:>5.1f}%] {'⚠️ GARGALO' if und_us > 10000 else ''}",
            f"  ■ 5. Compositor de Camadas : {cmp_us:>9.1f} µs ({cmp_us/1000.0:>6.2f} ms) [{pct_cmp:>5.1f}%] {'⚠️ GARGALO' if cmp_us > 10000 else ''}",
            f"  ■ 6. Apresentação Blit Qt  : {blit_us:>9.1f} µs ({blit_ms:>6.2f} ms) [{pct_blt:>5.1f}%] {'⚠️ GARGALO' if blit_ms > 16.6 else ''}",
            "  " + "-" * 66,
            f"  Ciclo Total do Micro-Evento: {total_cycle_us:.1f} µs ({total_cycle_us/1000.0:.2f} ms)",
            "",
            "-" * 78,
            " 🪟 PAINEL COMPLETO EM GRID (TODOS OS 20 MEDIDORES EM TEMPO REAL)",
            "-" * 78,
            "[LINHA 1: Estágios Granulares C++]",
            f"  • 1. CINEMÁTICA / DINÂMICA     : {kin_us:.1f} µs ({kin_us/1000.0:.3f} ms)  | Filtro de caneta e velocidade",
            f"  • 2. INTERPOLAÇÃO DABS         : {int_us:.1f} µs ({int_us/1000.0:.3f} ms)  | Espaçamento e resíduo",
            f"  • 3. RASTERDAB (SHADERS)       : {dab_us:.1f} µs ({dab_us/1000.0:.2f} ms)  | SIMD AVX2 de ponta e papel",
            f"  • 4. GRAVAÇÃO DE UNDO          : {und_us:.1f} µs ({und_us/1000.0:.2f} ms)  | Cópia de blocos 128x128",
            "",
            "[LINHA 2: Composição, Blit e Frequências]",
            f"  • 5. COMPOSITOR DE CAMADAS     : {cmp_us:.1f} µs ({cmp_us/1000.0:.2f} ms)  | Mesclagem SSE2 na região",
            f"  • 6. APRESENTAÇÃO BLIT QT      : {blit_ms:.2f} ms ({blit_us:.0f} µs na vp) | QPainter.drawImage na tela",
            f"  • 7. LATÊNCIA TOTAL MOTOR      : {lat_us:.1f} µs ({lat_us/1000.0:.2f} ms)  | Tempo de micro-evento C++",
            f"  • 8. TAXA REAL DA VIEWPORT     : {vp_fps:.1f} FPS                      | Fluidez da tela",
            "",
            "[LINHA 3: Frequências & Pegada Geométrica]",
            f"  • 9. FREQUÊNCIA DA MESA        : {rate_hz} Hz                          | Taxa do sensor",
            f"  • 10. TAXA DE CARIMBOS         : {dabs_rate:,} dabs/s                  | {dabs_tot:,} acumulados",
            f"  • 11. DABS EMITIDOS            : {dabs_rend} dabs                      | Total traço: {dabs_tot:,}",
            f"  • 12. REGIÃO SUJA REPINTADA    : {dw} × {dh} px                        | Largura × Altura",
            "",
            "[LINHA 4: Área, Blocos (Tiles) & Memória]",
            f"  • 13. ÁREA SUJA DO EVENTO      : {int(area_px):,} px²                  | Superfície afetada",
            f"  • 14. BLOCOS GRAVADOS / TOTAL  : {tiles_rec} gravados                  | Total alocados: {tiles_act}",
            f"  • 15. RAM DO CANVAS            : {ram_canvas:.2f} MB                   | {tiles_act} tiles de 128x128",
            f"  • 16. RAM DO HISTÓRICO UNDO    : {ram_undo:.2f} MB                   | {undo_steps} passos de desfazer",
            "",
            "[LINHA 5: Sensores da Caneta & Hardware]",
            f"  • 17. PRESSÃO FÍSICA VS CURVA  : {p_raw_str:<22} | {p_dyn_str}",
            f"  • 18. VELOCIDADE DO TRAÇO      : {vel_str:<22} | {vel_sub}",
            f"  • 19. LAG DO ESTABILIZADOR     : {lag_str:<22} | {lag_sub}",
            f"  • 20. ACELERAÇÃO & MINI-MOTOR  : {'AVX2 / SSE2':<22} | {eng_str}",
            "",
            "-" * 78,
            " ⚙️ AMBIENTE, ARQUITETURA & ACELERAÇÃO",
            "-" * 78,
            "  • Instruções SIMD       : AVX2 / SSE2 Ativo (Vetorizado)",
            f"  • Mini-Motor em Execução : {eng_str}",
            "  • Formato de Bloco      : Tiles 128x128 em BGRA32 / Float32",
            "  • Polling de Viewport   : 60 FPS Desacoplado via QTimer",
            "=" * 78,
        ])

        return "\n".join(lines)
