"""telemetry_report — texto do relatório completo de telemetria (os 20 medidores).

Um relatório só, usado pelos três botões "Copiar relatório" (cockpit em grade,
painel de telemetria e diálogo de diagnóstico). Os 20 medidores vêm de
`telemetry_meters.read_meters`, a mesma leitura que o cockpit desenha. Até 2026-09-24 havia dois
geradores com o mesmo texto: `TelemetryTracker.generate_full_report` e
`TelemetryReportGenerator.generate(janela)`, que lia os atributos privados da
janela (`window._peaks`, `window._state_history`...).
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from .telemetry_dto import TelemetrySnapshot
from .telemetry_meters import ENGINE_NAMES, TITLES, read_meters, simd_text

if TYPE_CHECKING:
    from .telemetry_tracker import TelemetryTracker

_ROWS = (
    "LINHA 1: Estágios Granulares C++",
    "LINHA 2: Composição, Blit e Frequências",
    "LINHA 3: Frequências & Pegada Geométrica",
    "LINHA 4: Área, Blocos (Tiles) & Memória",
    "LINHA 5: Sensores da Caneta & Hardware",
)


def build_report(
    tracker: "TelemetryTracker",
    snap: TelemetrySnapshot,
    vp: dict,
    stay_on_top: Optional[bool] = None,
) -> str:
    """Texto do relatório: estado e picos do `tracker`, medidores de `snap` e `vp`."""
    counts = tracker.state_counts
    peaks = tracker.peaks
    history = tracker.state_history

    blit_ms = vp.get("qt_draw_image_ms", 0.0)
    blit_us = blit_ms * 1000.0

    kin_us = snap.time_kinematics_us
    int_us = snap.time_interpolation_us
    dab_us = snap.time_raster_dab_us
    und_us = snap.time_undo_record_us
    cmp_us = snap.time_composite_us
    total_cycle_us = kin_us + int_us + dab_us + und_us + cmp_us + blit_us
    denom = total_cycle_us if total_cycle_us > 0 else 1.0

    pct_kin = (kin_us / denom) * 100.0
    pct_int = (int_us / denom) * 100.0
    pct_dab = (dab_us / denom) * 100.0
    pct_und = (und_us / denom) * 100.0
    pct_cmp = (cmp_us / denom) * 100.0
    pct_blt = (blit_us / denom) * 100.0

    eng_str = ENGINE_NAMES.get(snap.active_engine_id, "Motor Nativo C++")

    lines = [
        "=" * 78,
        " LUMENIA ART STUDIO — COCKPIT DE TELEMETRIA & DIAGNÓSTICO EM GRID",
        "=" * 78,
        f"Data / Hora da Captura  : {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Monitoramento em Tempo  : Captura Ativa (Timer 16ms / Zero Overhead)",
        *([f"Fixação Sempre no Topo  : {'SIM' if stay_on_top else 'NÃO'}"] if stay_on_top is not None else []),
        "",
        "-" * 78,
        " DIAGNÓSTICO DO PIPELINE & ALTERAÇÕES DE ESTADO",
        "-" * 78,
        f"Estado Atual do Banner  : {tracker.current_state_str}",
        f"Classificação de Estado : {tracker.current_state_key}",
        f"Condição Operacional    : {'Equilibrado (Zero Sobrecarga)' if tracker.current_state_key == 'PIPELINE_EQUILIBRADO' else 'Presença de Gargalo Operacional'}",
        "",
        "Resumo de Ocorrências na Sessão de Teste:",
        f"  • PIPELINE EQUILIBRADO (< 2ms) : {counts.get('PIPELINE_EQUILIBRADO', 0)} vez(es)",
        f"  • GARGALO EM RASTER (> 15ms)     : {counts.get('GARGALO_RASTER', 0)} vez(es)",
        f"  • GARGALO EM TELA / BLIT (> 16ms): {counts.get('GARGALO_BLIT', 0)} vez(es)",
        f"  • GARGALO EM UNDO (> 10ms)       : {counts.get('GARGALO_UNDO', 0)} vez(es)",
        f"  • GARGALO EM COMPOSITOR (> 10ms) : {counts.get('GARGALO_COMPOSITOR', 0)} vez(es)",
        f"  • Total de Transições Registradas : {len(history)}",
        "",
        "Picos Máximos de Estresse Registrados na Sessão:",
        f"  • Pico Latência do Motor C++ : {peaks['motor_latency_us']:.1f} µs ({peaks['motor_latency_us']/1000.0:.2f} ms)",
        f"  • Pico em RasterDab (Shaders): {peaks['raster_dab_us']:.1f} µs ({peaks['raster_dab_us']/1000.0:.2f} ms)",
        f"  • Pico Gravação de Undo      : {peaks['undo_record_us']:.1f} µs ({peaks['undo_record_us']/1000.0:.2f} ms)",
        f"  • Pico Compositor de Camadas : {peaks['composite_us']:.1f} µs ({peaks['composite_us']/1000.0:.2f} ms)",
        f"  • Pico Apresentação Blit Qt  : {peaks['blit_ms']:.2f} ms ({peaks['blit_ms']*1000.0:.0f} µs)",
        f"  • Menor Fluidez da Viewport  : {peaks['min_fps']:.1f} FPS",
        f"  • Pico Velocidade do Traço   : {int(peaks['stroke_velocity'])} px/s",
        f"  • Pico Lag do Estabilizador  : {peaks['stabilizer_lag_px']:.1f} px",
        f"  • Pico Taxa de Carimbos      : {int(peaks['dabs_per_second']):,} dabs/s",
        f"  • Pico Área Suja Repintada   : {int(peaks['dirty_area_px']):,} px² ({int(peaks['tiles_recorded'])} tiles gravados)",
        "",
        "Histórico Cronológico das Últimas Alterações de Estado (Transições):",
    ]

    if history:
        for trans in history[-15:]:
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
    for index, reading in enumerate(read_meters(snap, vp, tracker.last_active_pen)):
        if index % 4 == 0:
            lines.append(f"[{_ROWS[index // 4]}]")
        lines.append(f"  • {TITLES[reading.key].upper():<30} : {reading.value:<22} | {reading.detail}")
        if index % 4 == 3:
            lines.append("")

    lines.extend([
        "-" * 78,
        " AMBIENTE, ARQUITETURA & ACELERAÇÃO",
        "-" * 78,
        f"  • Instruções SIMD       : {simd_text(snap)}",
        f"  • Mini-Motor em Execução : {eng_str}",
        "  • Formato de Bloco      : Tiles 128x128 em BGRA32 / Float32",
        "  • Polling de Viewport   : 60 FPS Desacoplado via QTimer",
        "=" * 78,
    ])

    return "\n".join(lines)
