"""
ui.core.engine.telemetry_dto — DTO Canônico de Telemetria Universal
==================================================================
Contrato de dados puro em Python para telemetria em tempo real do ALADYN ENGINE.
Desacopla completamente a UI de structs nativas do C++/PyBind11 (ARCcC Pilar 2.4).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Dict


@dataclass
class TelemetrySnapshot:
    """Snapshot instantâneo e desacoplado de telemetria e diagnóstico do motor."""

    # 1. Desempenho Geral do Traço
    last_segment_latency_us: float = 0.0
    total_dabs_per_second: int = 0
    input_event_rate_hz: int = 0
    stroke_total_time_ms: float = 0.0
    total_dabs_in_stroke: int = 0

    # 2. Pipeline Granular (µs)
    time_kinematics_us: float = 0.0
    time_interpolation_us: float = 0.0
    time_raster_dab_us: float = 0.0
    time_undo_record_us: float = 0.0
    time_composite_us: float = 0.0

    # 3. Superfície, Viewport e Renderização
    last_dirty_width: float = 0.0
    last_dirty_height: float = 0.0
    last_dirty_area_px: float = 0.0
    last_tiles_recorded: int = 0
    last_dabs_rendered: int = 0

    # 4. Memória e Estrutura de Tiles
    active_tile_count: int = 0
    tile_grid_memory_mb: float = 0.0
    undo_stack_memory_mb: float = 0.0
    undo_steps_count: int = 0

    # 5. Sensor, Caneta e Cinemática
    raw_pressure: float = 0.0
    dynamic_pressure: float = 0.0
    stroke_velocity: float = 0.0
    stabilizer_lag_px: float = 0.0

    # 6. Motor ativo e aceleração (até 2026-09-24 ficavam fora do DTO, e o
    # relatório lia `active_engine_id` de um objeto que não o tinha: mostrava
    # sempre o nome padrão do motor)
    active_engine_id: int = 0
    simd_active: bool = False
    last_tiles_composited: int = 0
    dirty_tiles_last_stroke: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Converte o snapshot em um dicionário Python serializável."""
        return asdict(self)

    @classmethod
    def from_native(cls, native_snap: Any) -> TelemetrySnapshot:
        """Cria uma instância desacoplada a partir de uma struct nativa ou dicionário.

        A struct nativa (`RealTimeStrokeMetrics`) é lida campo a campo SEM valor
        padrão: campo renomeado no C++ vira erro aqui (e no teste de contrato
        `tests/test_telemetry_contract.py`), não um zero silencioso na tela.
        Dicionários (testes, telemetria gravada) podem omitir campos.
        """
        if native_snap is None:
            return cls()
        if isinstance(native_snap, cls):
            return native_snap
        if isinstance(native_snap, dict):
            return cls(**{
                f.name: type(f.default)(native_snap.get(f.name, f.default)) for f in fields(cls)
            })
        return cls(**{f.name: type(f.default)(getattr(native_snap, f.name)) for f in fields(cls)})
