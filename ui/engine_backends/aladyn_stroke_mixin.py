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

logger = logging.getLogger(__name__)


class AladynStrokeMixin:
    """Mixin responsável pelo ciclo de vida do traço e telemetria no AladynBackend."""

    def start_stroke(self, x: float, y: float, pressure: float) -> None:
        self._last_x = float(x)
        self._last_y = float(y)
        if self._facade:
            if hasattr(self._facade, "begin_stroke_raw"):
                self._facade.begin_stroke_raw(float(x), float(y), float(pressure))
            elif self._native:
                pt = self._native.Point2D(float(x), float(y))
                evt = self._native.PointerEvent(
                    self._native.PointerEventType.Press, pt, float(pressure), time.time()
                )
                self._facade.begin_stroke(evt)

    def paint_stroke(self, x: float, y: float, pressure: float) -> list[float]:
        self._last_x = float(x)
        self._last_y = float(y)
        if self._facade:
            if hasattr(self._facade, "update_stroke_raw"):
                res = self._facade.update_stroke_raw(float(x), float(y), float(pressure))
                if res and len(res) >= 9:
                    self.last_telemetry = (float(res[6]), float(res[7]), float(res[8]))
                    return res
            elif self._native:
                pt = self._native.Point2D(float(x), float(y))
                evt = self._native.PointerEvent(
                    self._native.PointerEventType.Move, pt, float(pressure), time.time()
                )
                telemetry = self._facade.update_stroke(evt)
                if telemetry:
                    self.last_telemetry = (
                        float(telemetry.pressure),
                        float(telemetry.velocity),
                        float(telemetry.output_flow),
                    )
        return []

    def end_stroke(self, x: float | None = None, y: float | None = None) -> None:
        if self._facade:
            if hasattr(self._facade, "end_stroke_raw"):
                self._facade.end_stroke_raw()
            elif self._native:
                rx = float(x) if x is not None else getattr(self, "_last_x", 0.0)
                ry = float(y) if y is not None else getattr(self, "_last_y", 0.0)
                pt = self._native.Point2D(rx, ry)
                evt = self._native.PointerEvent(
                    self._native.PointerEventType.Release, pt, 0.0, time.time()
                )
                self._facade.end_stroke(evt)

            # Emite log executivo sumarizado de 1 linha quando a telemetria estiver ativa
            if hasattr(self._facade, "is_telemetry_enabled") and self._facade.is_telemetry_enabled():
                snap = self._facade.get_telemetry_snapshot()
                if snap and snap.total_dabs_in_stroke > 0:
                    logger.info(
                        f"🖋️ [Traço C++] {snap.total_dabs_in_stroke} dabs em {snap.stroke_total_time_ms:.1f}ms | "
                        f"Latência dab: {snap.last_segment_latency_us:.1f}µs | "
                        f"Taxa: {snap.total_dabs_per_second:.0f} dabs/s"
                    )

        if not getattr(self, "_is_filling", False):
            self._action_stack.append(("stroke", 1))
            self._redo_stack.clear()

    def begin_stroke_raw(self, x: float, y: float, pressure: float = 1.0) -> None:
        self.start_stroke(x, y, pressure)

    def update_stroke_raw(self, x: float, y: float, pressure: float = 1.0) -> list[float]:
        return self.paint_stroke(x, y, pressure)

    def end_stroke_raw(self) -> None:
        self.end_stroke()

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
        if self._facade and self._native and hasattr(self._facade, "flood_fill"):
            if hasattr(fill_color, "red"):
                c = self._native.ColorRGBA(fill_color.red(), fill_color.green(), fill_color.blue(), fill_color.alpha())
            elif isinstance(fill_color, (tuple, list)) and len(fill_color) >= 3:
                r = int(fill_color[0] * 255) if isinstance(fill_color[0], float) else int(fill_color[0])
                g = int(fill_color[1] * 255) if isinstance(fill_color[1], float) else int(fill_color[1])
                b = int(fill_color[2] * 255) if isinstance(fill_color[2], float) else int(fill_color[2])
                a = int(fill_color[3] * 255) if len(fill_color) > 3 and isinstance(fill_color[3], float) else (int(fill_color[3]) if len(fill_color) > 3 else 255)
                c = self._native.ColorRGBA(r, g, b, a)
            else:
                c = self._native.ColorRGBA(0, 0, 0, 255)
            return self._facade.flood_fill(
                int(seed_x), int(seed_y), c, int(tolerance), bool(contiguous),
                int(expand_px), int(gap_closing_px), bool(anti_aliasing), bool(sample_all_layers)
            )
        return False

    def fill_area(
        self, seed_x: int, seed_y: int, fill_color: Any, tolerance: int = 20,
        contiguous: bool = True, expand_px: int = 1, gap_closing_px: int = 0,
        aa: bool = True, sample_all: bool = True,
    ) -> bool:
        """Executa Flood Fill ultra-rápido (<1ms) diretamente no motor nativo C++."""
        if not self._facade or not self._native or not hasattr(self._facade, "flood_fill"):
            return False
        if hasattr(fill_color, "red"):
            native_color = self._native.ColorRGBA(
                int(fill_color.red()), int(fill_color.green()), int(fill_color.blue()), int(fill_color.alpha())
            )
        else:
            native_color = self._native.ColorRGBA(0, 0, 0, 255)
        return self._facade.flood_fill(
            int(seed_x), int(seed_y), native_color, int(tolerance), bool(contiguous),
            int(expand_px), int(gap_closing_px), bool(aa), bool(sample_all)
        )

    def set_telemetry_enabled(self, enabled: bool) -> None:
        if self._facade and hasattr(self._facade, "set_telemetry_enabled"):
            self._facade.set_telemetry_enabled(enabled)

    def is_telemetry_enabled(self) -> bool:
        if self._facade and hasattr(self._facade, "is_telemetry_enabled"):
            return self._facade.is_telemetry_enabled()
        return False

    def set_detailed_logging_enabled(self, detailed: bool) -> None:
        if self._facade and hasattr(self._facade, "set_detailed_logging_enabled"):
            self._facade.set_detailed_logging_enabled(detailed)

    def is_detailed_logging_enabled(self) -> bool:
        if self._facade and hasattr(self._facade, "is_detailed_logging_enabled"):
            return self._facade.is_detailed_logging_enabled()
        return False

    def get_telemetry_snapshot(self) -> Any:
        if self._facade and hasattr(self._facade, "get_telemetry_snapshot"):
            return self._facade.get_telemetry_snapshot()
        return None

    def reset_telemetry(self) -> None:
        if self._facade and hasattr(self._facade, "reset_telemetry"):
            self._facade.reset_telemetry()
