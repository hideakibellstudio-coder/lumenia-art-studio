"""
ui.core.engine.telemetry_dto — DTO Canônico de Telemetria Universal
==================================================================
Contrato de dados puro em Python para telemetria em tempo real do ALADYN ENGINE.
Desacopla completamente a UI de structs nativas do C++/PyBind11 (ARCcC Pilar 2.4).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


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

    def to_dict(self) -> Dict[str, Any]:
        """Converte o snapshot em um dicionário Python serializável."""
        return asdict(self)

    @classmethod
    def from_native(cls, native_snap: Any) -> TelemetrySnapshot:
        """Cria uma instância desacoplada a partir de uma struct nativa ou dicionário."""
        if native_snap is None:
            return cls()

        if isinstance(native_snap, cls):
            return native_snap

        if isinstance(native_snap, dict):
            return cls(
                last_segment_latency_us=float(native_snap.get("last_segment_latency_us", 0.0)),
                total_dabs_per_second=int(native_snap.get("total_dabs_per_second", 0)),
                input_event_rate_hz=int(native_snap.get("input_event_rate_hz", 0)),
                stroke_total_time_ms=float(native_snap.get("stroke_total_time_ms", 0.0)),
                total_dabs_in_stroke=int(native_snap.get("total_dabs_in_stroke", 0)),
                time_kinematics_us=float(native_snap.get("time_kinematics_us", 0.0)),
                time_interpolation_us=float(native_snap.get("time_interpolation_us", 0.0)),
                time_raster_dab_us=float(native_snap.get("time_raster_dab_us", 0.0)),
                time_undo_record_us=float(native_snap.get("time_undo_record_us", 0.0)),
                time_composite_us=float(native_snap.get("time_composite_us", 0.0)),
                last_dirty_width=float(native_snap.get("last_dirty_width", 0.0)),
                last_dirty_height=float(native_snap.get("last_dirty_height", 0.0)),
                last_dirty_area_px=float(native_snap.get("last_dirty_area_px", 0.0)),
                last_tiles_recorded=int(native_snap.get("last_tiles_recorded", 0)),
                last_dabs_rendered=int(native_snap.get("last_dabs_rendered", 0)),
                active_tile_count=int(native_snap.get("active_tile_count", 0)),
                tile_grid_memory_mb=float(native_snap.get("tile_grid_memory_mb", 0.0)),
                undo_stack_memory_mb=float(native_snap.get("undo_stack_memory_mb", 0.0)),
                undo_steps_count=int(native_snap.get("undo_steps_count", 0)),
                raw_pressure=float(native_snap.get("raw_pressure", 0.0)),
                dynamic_pressure=float(native_snap.get("dynamic_pressure", 0.0)),
                stroke_velocity=float(native_snap.get("stroke_velocity", 0.0)),
                stabilizer_lag_px=float(native_snap.get("stabilizer_lag_px", 0.0)),
            )

        # Struct nativa PyBind11 / C++
        return cls(
            last_segment_latency_us=float(getattr(native_snap, "last_segment_latency_us", 0.0)),
            total_dabs_per_second=int(getattr(native_snap, "total_dabs_per_second", 0)),
            input_event_rate_hz=int(getattr(native_snap, "input_event_rate_hz", 0)),
            stroke_total_time_ms=float(getattr(native_snap, "stroke_total_time_ms", 0.0)),
            total_dabs_in_stroke=int(getattr(native_snap, "total_dabs_in_stroke", 0)),
            time_kinematics_us=float(getattr(native_snap, "time_kinematics_us", 0.0)),
            time_interpolation_us=float(getattr(native_snap, "time_interpolation_us", 0.0)),
            time_raster_dab_us=float(getattr(native_snap, "time_raster_dab_us", 0.0)),
            time_undo_record_us=float(getattr(native_snap, "time_undo_record_us", 0.0)),
            time_composite_us=float(getattr(native_snap, "time_composite_us", 0.0)),
            last_dirty_width=float(getattr(native_snap, "last_dirty_width", 0.0)),
            last_dirty_height=float(getattr(native_snap, "last_dirty_height", 0.0)),
            last_dirty_area_px=float(getattr(native_snap, "last_dirty_area_px", 0.0)),
            last_tiles_recorded=int(getattr(native_snap, "last_tiles_recorded", 0)),
            last_dabs_rendered=int(getattr(native_snap, "last_dabs_rendered", 0)),
            active_tile_count=int(getattr(native_snap, "active_tile_count", 0)),
            tile_grid_memory_mb=float(getattr(native_snap, "tile_grid_memory_mb", 0.0)),
            undo_stack_memory_mb=float(getattr(native_snap, "undo_stack_memory_mb", 0.0)),
            undo_steps_count=int(getattr(native_snap, "undo_steps_count", 0)),
            raw_pressure=float(getattr(native_snap, "raw_pressure", 0.0)),
            dynamic_pressure=float(getattr(native_snap, "dynamic_pressure", 0.0)),
            stroke_velocity=float(getattr(native_snap, "stroke_velocity", 0.0)),
            stabilizer_lag_px=float(getattr(native_snap, "stabilizer_lag_px", 0.0)),
        )
