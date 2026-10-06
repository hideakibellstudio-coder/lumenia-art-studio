"""telemetry_meters — os 20 medidores da telemetria, definidos uma vez.

Cada medidor tem uma chave, um título e uma leitura (valor, detalhe, nível e
barra) calculada do `TelemetrySnapshot`, da viewport e da última caneta do
`TelemetryTracker`. O cockpit em grade desenha os cards a partir daqui e o
relatório imprime a mesma leitura. Até 2026-09-24 o cockpit calculava os
valores num lugar e o relatório repetia as fórmulas (e os títulos) em outro.

Os níveis são semânticos (`good`, `warning`, `critical`); a cor é da tela.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .telemetry_dto import TelemetrySnapshot

ENGINE_NAMES = {0: "BrushEngine", 1: "PencilEngine", 2: "InkerEngine", 3: "EraserEngine"}

# (chave, título, detalhe inicial) na ordem do cockpit (4 colunas × 5 linhas).
METERS: tuple[tuple[str, str, str], ...] = (
    ("kin", "1. Cinemática / Dinâmica", "Filtro de caneta e velocidade"),
    ("int", "2. Interpolação Dabs", "Espaçamento e resíduo"),
    ("dab", "3. RasterDab (Shaders)", "Carimbo de ponta e papel"),
    ("und", "4. Gravação de Undo", "Cópia de blocos 128x128"),
    ("cmp", "5. Compositor de Camadas", "Mesclagem na região suja"),
    ("blt", "6. Apresentação Blit Qt", "Cópia do canvas + drawImage"),
    ("lat", "7. Latência Total Motor", "Tempo de micro-evento C++"),
    ("fps", "8. Taxa Real da Viewport", "Taxa efetiva de redesenho"),
    ("hz", "9. Frequência da Mesa", "Taxa de eventos do hardware"),
    ("dabs_sec", "10. Taxa de Carimbos", "Rendimento do rasterizador"),
    ("dabs", "11. Dabs Emitidos", "Último micro-evento"),
    ("dirty", "12. Região Suja Repintada", "Bounding box atual"),
    ("area", "13. Área Suja do Evento", "Superfície de pixels repintada"),
    ("tiles", "14. Blocos Gravados / Total", "Blocos 128x128 em RAM"),
    ("ram_canvas", "15. RAM do Canvas", "Memória dos tiles do documento"),
    ("ram_undo", "16. RAM do Histórico Undo", "0 passos de desfazer"),
    ("press", "17. Pressão Física vs Curva", "Modulada: 0 %"),
    ("vel", "18. Velocidade do Traço", "Velocidade vetorial"),
    ("lag", "19. Lag do Estabilizador", "Distância do filtro inercial"),
    ("hw", "20. Aceleração & Mini-Motor", "Mini-motor C++ ativo"),
)
TITLES = {key: title for key, title, _detail in METERS}


@dataclass(frozen=True)
class MeterReading:
    key: str
    value: str
    detail: str
    level: str = ""  # "", "good", "warning" ou "critical"
    bar: Optional[int] = None


def presentation_ms(vp: dict) -> float:
    """Custo de levar a imagem do motor à tela: a cópia do canvas + o `drawImage`.

    O medidor "Blit" cronometrava só o `drawImage` e a cópia (`get_qimage_lod`, o
    maior custo da repintura: 34 ms em 4K em 2026-10-01) ficava fora do número
    (achado D16). Toda tela e o relatório leem daqui, para não haver duas contas.
    """
    return vp.get("qt_acquire_image_ms", 0.0) + vp.get("qt_draw_image_ms", 0.0)


def simd_text(snap: TelemetrySnapshot) -> str:
    """O motor informa se a mesclagem das camadas usa AVX2 agora (`simd_active`): a CPU decide na hora de rodar."""
    return "AVX2 (vetorizado)" if snap.simd_active else "Escalar (sem AVX2)"


def read_meters(snap: TelemetrySnapshot, vp: dict, last_pen: dict) -> list[MeterReading]:
    """Leitura dos 20 medidores, na ordem de `METERS`."""
    blit_ms = presentation_ms(vp)
    fps = vp.get("qt_fps", 0.0)
    kin, itp, dab = snap.time_kinematics_us, snap.time_interpolation_us, snap.time_raster_dab_us
    und, cmp, lat = snap.time_undo_record_us, snap.time_composite_us, snap.last_segment_latency_us
    tiles = snap.active_tile_count

    pressure, velocity = int(snap.raw_pressure * 100), int(snap.stroke_velocity)
    if pressure > 0 or velocity > 0:
        pen = (pressure, int(snap.dynamic_pressure * 100), velocity, snap.stabilizer_lag_px, "")
    elif last_pen["raw_pressure"] > 0:  # caneta solta: mostra o último traço
        pen = (int(last_pen["raw_pressure"]), int(last_pen["dynamic_pressure"]),
               int(last_pen["velocity"]), last_pen["stabilizer_lag"], " (último traço)")
    else:
        pen = (0, 0, 0, 0.0, "")
    p_raw, p_dyn, vel, lag, suffix = pen

    return [
        MeterReading("kin", f"{kin:.1f} µs", f"{kin/1000.0:.3f} ms"),
        MeterReading("int", f"{itp:.1f} µs", f"{itp/1000.0:.3f} ms"),
        MeterReading("dab", f"{dab:.1f} µs", f"{dab/1000.0:.2f} ms", "critical" if dab > 15000 else ""),
        MeterReading("und", f"{und:.1f} µs", f"{und/1000.0:.2f} ms", "critical" if und > 10000 else ""),
        MeterReading("cmp", f"{cmp:.1f} µs", f"{cmp/1000.0:.2f} ms", "critical" if cmp > 10000 else ""),
        MeterReading("blt", f"{blit_ms:.2f} ms",
                     f"cópia {vp.get('qt_acquire_image_ms', 0.0):.2f} + desenho {vp.get('qt_draw_image_ms', 0.0):.2f} ms"
                     f" · paint {vp.get('qt_paint_total_ms', 0.0):.2f} ms",
                     "critical" if blit_ms > 16.6 else ("warning" if blit_ms > 10.0 else "")),
        MeterReading("lat", f"{lat:.1f} µs", f"{lat/1000.0:.2f} ms"),
        MeterReading("fps", f"{fps:.1f} FPS", "Fluidez da tela",
                     "good" if fps >= 55 else ("warning" if fps >= 30 else "critical")),
        MeterReading("hz", f"{snap.input_event_rate_hz} Hz", "Taxa do sensor"),
        MeterReading("dabs_sec", f"{snap.total_dabs_per_second:,} dabs/s",
                     f"{snap.total_dabs_in_stroke:,} acumulados"),
        MeterReading("dabs", f"{snap.last_dabs_rendered} dabs", f"Total traço: {snap.total_dabs_in_stroke:,}"),
        MeterReading("dirty", f"{int(snap.last_dirty_width)} × {int(snap.last_dirty_height)} px",
                     "Largura × Altura"),
        MeterReading("area", f"{int(snap.last_dirty_area_px):,} px²", "Superfície afetada"),
        MeterReading("tiles", f"{snap.last_tiles_recorded} gravados", f"Total alocados: {tiles}"),
        MeterReading("ram_canvas", f"{snap.tile_grid_memory_mb:.2f} MB", f"{tiles} tiles de 128x128"),
        MeterReading("ram_undo", f"{snap.undo_stack_memory_mb:.2f} MB",
                     f"{snap.undo_steps_count} passos de desfazer"),
        MeterReading("press", f"{p_raw} %", f"Modulada: {p_dyn} %{suffix}", bar=p_raw),
        MeterReading("vel", f"{vel} px/s", f"Velocidade vetorial{suffix}", bar=vel),
        MeterReading("lag", f"{lag:.1f} px", f"Lag do estabilizador{suffix}"),
        MeterReading("hw", simd_text(snap), ENGINE_NAMES.get(snap.active_engine_id, "Motor Nativo C++")),
    ]
