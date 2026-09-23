"""
AladynStrokeMixin — Gerenciador Atômico de Traços, Fast-Path e Telemetria para o AladynBackend.
================================================================================================
Isola todo o pipeline de execução de pinceladas (start_stroke, paint_stroke, end_stroke),
o fast-path de bypass (begin_stroke_raw, update_stroke_raw, end_stroke_raw), preenchimento
por balde de tinta (flood_fill, fill_area) e telemetria de latência do C++.
"""

from __future__ import annotations
import time
import logging
from typing import Any
from ui.core.engine.telemetry_dto import TelemetrySnapshot
from .aladyn_buffers import to_native_color_rgba
from .native_fallback import nativo_tem

logger = logging.getLogger(__name__)


class AladynStrokeMixin:
    """Mixin responsável pelo ciclo de vida do traço e telemetria no AladynBackend."""

    def start_stroke(
        self,
        x: float,
        y: float,
        pressure: float,
        timestamp: float = 0.0,
        tilt_x: float = 0.0,
        tilt_y: float = 0.0,
        twist: float = 0.0,
    ) -> None:
        self._last_x = float(x)
        self._last_y = float(y)
        if self._facade:
            if hasattr(self._facade, "begin_stroke_raw"):
                self._facade.begin_stroke_raw(
                    float(x), float(y), float(pressure), float(timestamp),
                    float(tilt_x), float(tilt_y), float(twist)
                )
            elif self._native:
                pt = self._native.Point2D(float(x), float(y))
                evt = self._native.PointerEvent(
                    self._native.PointerEventType.Press, pt, float(pressure), float(timestamp) if timestamp > 0 else time.time(),
                    float(tilt_x), float(tilt_y), float(twist)
                )
                self._facade.begin_stroke(evt)

    def paint_stroke(
        self,
        x: float,
        y: float,
        pressure: float,
        timestamp: float = 0.0,
        tilt_x: float = 0.0,
        tilt_y: float = 0.0,
        twist: float = 0.0,
    ) -> list[float]:
        self._last_x = float(x)
        self._last_y = float(y)
        if self._facade:
            if hasattr(self._facade, "update_stroke_raw"):
                res = self._facade.update_stroke_raw(
                    float(x), float(y), float(pressure), float(timestamp),
                    float(tilt_x), float(tilt_y), float(twist)
                )
                if res and len(res) >= 9:
                    self.last_telemetry = (float(res[6]), float(res[7]), float(res[8]))
                    return res
            elif self._native:
                pt = self._native.Point2D(float(x), float(y))
                evt = self._native.PointerEvent(
                    self._native.PointerEventType.Move, pt, float(pressure), float(timestamp) if timestamp > 0 else time.time(),
                    float(tilt_x), float(tilt_y), float(twist)
                )
                telemetry = self._facade.update_stroke(evt)
                if telemetry:
                    self.last_telemetry = (
                        float(telemetry.pressure),
                        float(telemetry.velocity),
                        float(telemetry.output_flow),
                    )
        return []

    def end_stroke(self, x: float | None = None, y: float | None = None) -> list[float]:
        res = []
        if self._facade:
            if hasattr(self._facade, "end_stroke_raw"):
                res = self._facade.end_stroke_raw()
            elif self._native:
                rx = float(x) if x is not None else getattr(self, "_last_x", 0.0)
                ry = float(y) if y is not None else getattr(self, "_last_y", 0.0)
                pt = self._native.Point2D(rx, ry)
                evt = self._native.PointerEvent(
                    self._native.PointerEventType.Release, pt, 0.0, time.time()
                )
                self._facade.end_stroke(evt)

            # Emite log executivo sumarizado de 1 linha quando a telemetria estiver ativa
            if nativo_tem(self._facade, "is_telemetry_enabled", "sem resumo de telemetria por traço") and self._facade.is_telemetry_enabled():
                snap = self._facade.get_telemetry_snapshot()
                if snap and snap.total_dabs_in_stroke > 0:
                    breakdown = (
                        f" [Estágios µs: Kin={getattr(snap, 'time_kinematics_us', 0.0):.0f} | Interp={getattr(snap, 'time_interpolation_us', 0.0):.0f} | "
                        f"Dab={getattr(snap, 'time_raster_dab_us', 0.0):.0f} | Undo={getattr(snap, 'time_undo_record_us', 0.0):.0f} | Comp={getattr(snap, 'time_composite_us', 0.0):.0f}]"
                        if getattr(snap, "time_raster_dab_us", 0.0) > 0.0 or getattr(snap, "time_composite_us", 0.0) > 0.0 else ""
                    )
                    logger.info(
                        f"🖋️ [Traço C++] {snap.total_dabs_in_stroke} dabs em {snap.stroke_total_time_ms:.1f}ms | "
                        f"Latência dab: {snap.last_segment_latency_us:.1f}µs | "
                        f"Taxa: {snap.total_dabs_per_second:.0f} dabs/s{breakdown}"
                    )

        if not getattr(self, "_is_filling", False):
            if hasattr(self, "_action_stack"):
                self._action_stack.append(("stroke", 1))
                max_steps = self.get_undo_max_steps() if hasattr(self, "get_undo_max_steps") else 50
                if len(self._action_stack) > max_steps:
                    self._action_stack.pop(0)
            if hasattr(self, "_redo_stack"):
                self._redo_stack.clear()
            if hasattr(self, "_mark_document_dirty"):
                self._mark_document_dirty("stroke")
        return res or []

    def begin_stroke_raw(
        self,
        x: float,
        y: float,
        pressure: float = 1.0,
        timestamp: float = 0.0,
        tilt_x: float = 0.0,
        tilt_y: float = 0.0,
        twist: float = 0.0,
    ) -> None:
        self.start_stroke(x, y, pressure, timestamp, tilt_x, tilt_y, twist)

    def update_stroke_raw(
        self,
        x: float,
        y: float,
        pressure: float = 1.0,
        timestamp: float = 0.0,
        tilt_x: float = 0.0,
        tilt_y: float = 0.0,
        twist: float = 0.0,
    ) -> list[float]:
        return self.paint_stroke(x, y, pressure, timestamp, tilt_x, tilt_y, twist)

    def end_stroke_raw(self) -> list[float]:
        return self.end_stroke()

    def flood_fill(
        self,
        seed_x: int,
        seed_y: int,
        fill_color: Any,
        tolerance: int = 20,
        contiguous: bool = True,
        expand_px: int = 1,
        gap_closing_px: int = 0,
        anti_aliasing: bool = True,
        sample_all_layers: bool = True,
    ) -> bool:
        if self._facade and self._native:
            c = to_native_color_rgba(self._native, fill_color)
            res = self._facade.flood_fill(
                int(seed_x), int(seed_y), c, int(tolerance), bool(contiguous),
                int(expand_px), int(gap_closing_px), bool(anti_aliasing), bool(sample_all_layers)
            )
            if res and hasattr(self, "_mark_document_dirty"):
                self._mark_document_dirty("flood_fill")
            return res
        return False

    def fill_area(
        self, seed_x: int, seed_y: int, fill_color: Any, tolerance: int = 20,
        contiguous: bool = True, expand_px: int = 1, gap_closing_px: int = 0,
        aa: bool = True, sample_all: bool = True,
    ) -> bool:
        """Executa Flood Fill ultra-rápido (<1ms) diretamente no motor nativo C++."""
        if not self._facade or not self._native or not nativo_tem(self._facade, "flood_fill", "o balde de tinta não pinta"):
            return False
        native_color = to_native_color_rgba(self._native, fill_color)
        res = self._facade.flood_fill(
            int(seed_x), int(seed_y), native_color, int(tolerance), bool(contiguous),
            int(expand_px), int(gap_closing_px), bool(aa), bool(sample_all)
        )
        if res and hasattr(self, "_mark_document_dirty"):
            self._mark_document_dirty("flood_fill")
        return res

    def set_telemetry_enabled(self, enabled: bool) -> None:
        if self._facade:
            self._facade.set_telemetry_enabled(enabled)

    def is_telemetry_enabled(self) -> bool:
        if self._facade:
            return self._facade.is_telemetry_enabled()
        return False

    def set_detailed_logging_enabled(self, detailed: bool) -> None:
        if self._facade:
            self._facade.set_detailed_logging_enabled(detailed)

    def is_detailed_logging_enabled(self) -> bool:
        if self._facade:
            return self._facade.is_detailed_logging_enabled()
        return False

    def get_telemetry_snapshot(self) -> TelemetrySnapshot:
        if self._facade:
            native_snap = self._facade.get_telemetry_snapshot()
            return TelemetrySnapshot.from_native(native_snap)
        return TelemetrySnapshot()

    def reset_telemetry(self) -> None:
        if self._facade:
            self._facade.reset_telemetry()
