"""
AladynBackend — Adaptador do ALADYN ENGINE (C++ PyBind11 / aladyn_engine_native)
================================================================================
Adaptador que implementa a interface `EngineBackend` da Lumenia UI e conversa
diretamente com a `PaintEngineFacade` do ALADYN ENGINE.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from PySide6.QtGui import QImage
from ui.core.engine.backend import EngineBackend, PointerEvent

logger = logging.getLogger(__name__)


class AladynBackend(EngineBackend):
    """Backend nativo que encapsula a PaintEngineFacade do ALADYN ENGINE."""

    name = "aladyn"

    def __init__(self) -> None:
        self._native: Any = None
        self._facade: Any = None
        self._width: int = 800
        self._height: int = 600
        self.last_telemetry: tuple[float, float, float] = (0.0, 0.0, 0.0)

        try:
            import aladyn_engine_native
            self._native = aladyn_engine_native
            logger.info("[AladynBackend] Módulo nativo aladyn_engine_native carregado com sucesso.")
        except Exception as e:
            logger.info(
                f"[AladynBackend] aladyn_engine_native indisponível "
                f"({type(e).__name__}: {e}). Modo casca pura mantido."
            )
            self._native = None

    # ── Disponibilidade & ciclo de vida ──────────────────────────────────

    @property
    def available(self) -> bool:
        return self._native is not None

    def init_renderer(self, hwnd: int, width: int, height: int, canvas_w: int, canvas_h: int) -> None:
        if self._native is None:
            return
        try:
            self._width = max(1, canvas_w)
            self._height = max(1, canvas_h)
            self._facade = self._native.PaintEngineFacade(self._width, self._height)
            if hasattr(self._facade, "get_canvas_texture"):
                c_tex = self._facade.get_canvas_texture()
                if c_tex:
                    c_tex.canvas_grain_enabled = False
            logger.info(f"[AladynBackend] PaintEngineFacade inicializada com canvas {self._width}x{self._height}.")
        except Exception as e:
            logger.error(f"[AladynBackend] Falha ao inicializar PaintEngineFacade: {e}")
            self._facade = None

    def resize(self, width: int, height: int) -> None:
        if self._facade:
            self._width = max(1, width)
            self._height = max(1, height)
            self._facade.resize_canvas(self._width, self._height)

    def render(self, pan_x: float, pan_y: float, zoom: float, rotation_rad: float) -> None:
        # A renderização do ALADYN ENGINE ocorre diretamente via buffer de pixels RGBA em get_pixel_buffer()
        pass

    # ── Traço (stroke) ───────────────────────────────────────────────────

    def start_stroke(self, x: float, y: float, pressure: float) -> None:
        self._last_x = float(x)
        self._last_y = float(y)
        if self._facade and self._native:
            pt = self._native.Point2D(float(x), float(y))
            evt = self._native.PointerEvent(
                self._native.PointerEventType.Press, pt, float(pressure), time.time()
            )
            self._facade.begin_stroke(evt)

    def paint_stroke(self, x: float, y: float, pressure: float) -> None:
        self._last_x = float(x)
        self._last_y = float(y)
        if self._facade and self._native:
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

    def end_stroke(self, x: float | None = None, y: float | None = None) -> None:
        if self._facade and self._native:
            rx = float(x) if x is not None else getattr(self, "_last_x", 0.0)
            ry = float(y) if y is not None else getattr(self, "_last_y", 0.0)
            pt = self._native.Point2D(rx, ry)
            evt = self._native.PointerEvent(
                self._native.PointerEventType.Release, pt, 0.0, time.time()
            )
            self._facade.end_stroke(evt)

    def clear_canvas(self) -> None:
        if self._facade:
            self._facade.clear_canvas()

    def clear_layer(self, index: int) -> None:
        if self._facade:
            self._facade.clear_layer(index)

    def set_layer_alpha_lock(self, index: int, locked: bool) -> None:
        if self._facade:
            self._facade.set_layer_alpha_lock(index, locked)

    def set_layer_clipping_mask(self, index: int, clipped: bool) -> None:
        if self._facade:
            self._facade.set_layer_clipping_mask(index, clipped)

    def reorder_layer(self, from_index: int, to_index: int) -> bool:
        if self._facade:
            return self._facade.reorder_layer(from_index, to_index)
        return False

    def reorder_layers(self, new_order: list[int]) -> bool:
        if self._facade and hasattr(self._facade, "reorder_layers"):
            return self._facade.reorder_layers(new_order)
        return False

    def add_group(self, name: str = "Novo Grupo") -> int:
        if self._facade and hasattr(self._facade, "add_group"):
            return self._facade.add_group(name)
        return -1

    def is_group(self, index: int) -> bool:
        if self._facade and hasattr(self._facade, "is_group"):
            return self._facade.is_group(index)
        return False

    def set_group_pass_through(self, index: int, pass_through: bool) -> bool:
        if self._facade and hasattr(self._facade, "set_group_pass_through"):
            return self._facade.set_group_pass_through(index, pass_through)
        return False

    def duplicate_layer(self, index: int) -> int:
        if self._facade and hasattr(self._facade, "duplicate_layer"):
            return self._facade.duplicate_layer(index)
        return -1

    def merge_layer_down(self, index: int) -> bool:
        if self._facade:
            return self._facade.merge_layer_down(index)
        return False

    def set_background_color(self, r: int, g: int, b: int, a: int = 255) -> None:
        if self._facade and hasattr(self._facade, "set_background_color"):
            self._facade.set_background_color(int(r), int(g), int(b), int(a))

    def set_canvas_grain_enabled(self, enabled: bool) -> None:
        if self._facade and hasattr(self._facade, "get_canvas_texture"):
            c_tex = self._facade.get_canvas_texture()
            if c_tex:
                c_tex.canvas_grain_enabled = bool(enabled)

    def set_brush_grain_enabled(self, enabled: bool) -> None:
        if self._facade and hasattr(self._facade, "get_brush_profile"):
            prof = self._facade.get_brush_profile()
            if prof:
                prof.brush_grain_enabled = bool(enabled)

    # ── Pincel & Motor ───────────────────────────────────────────────────

    def set_engine_type(self, type_id: int) -> None:
        if self._facade:
            self._facade.set_engine_type(type_id)

    def get_active_engine_type(self) -> int:
        if self._facade:
            return self._facade.get_active_engine_type()
        return 0

    def set_brush_color(self, r: float, g: float, b: float) -> None:
        if self._facade and self._native:
            prof = self._facade.get_brush_profile()
            r_int = int(r * 255) if 0.0 <= r <= 1.0 else int(r)
            g_int = int(g * 255) if 0.0 <= g <= 1.0 else int(g)
            b_int = int(b * 255) if 0.0 <= b <= 1.0 else int(b)
            prof.base_color = self._native.ColorRGBA(r_int, g_int, b_int, 255)

    def set_brush_size(self, size: float) -> None:
        if self._facade:
            prof = self._facade.get_brush_profile()
            prof.brush_size = float(size)

    def set_brush_opacity(self, opacity: float) -> None:
        if self._facade:
            prof = self._facade.get_brush_profile()
            prof.opacity = float(opacity)

    def set_brush_spacing(self, spacing: float) -> None:
        if self._facade:
            prof = self._facade.get_brush_profile()
            prof.spacing_factor = float(spacing)

    def set_stabilizer_weight(self, weight: float) -> None:
        if self._facade:
            stab = self._facade.get_stabilizer()
            stab.set_stabilization_percentage(float(weight * 100.0 if weight <= 1.0 else weight))

    def set_brush_contrast(self, contrast: float) -> None:
        if self._facade:
            prof = self._facade.get_brush_profile()
            prof.hardness = float(contrast / 10.0 if contrast > 1.0 else contrast)

    def set_brush_pressure(self, pressure: float) -> None: pass
    def set_brush_invert_height(self, invert: bool) -> None: pass
    def set_pressure_curve_power(self, power: float) -> None: pass
    def set_min_density_active(self, active: bool) -> None: pass
    def set_min_density_value(self, value: float) -> None: pass

    # ── Texturas ─────────────────────────────────────────────────────────

    def set_shape_texture(self, pixels: bytes, width: int, height: int) -> None:
        if self._facade:
            self._facade.load_shape_texture(width, height, pixels)

    def set_heightmap_texture(self, pixels: bytes, width: int, height: int) -> None:
        if self._facade:
            self._facade.load_brush_height_texture(width, height, pixels)

    # ── Viewport / Câmera ────────────────────────────────────────────────

    def update_view(self, zoom: float, pan_x: float, pan_y: float, rotation: float) -> None:
        pass

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> PointerEvent:
        return PointerEvent(x=screen_x, y=screen_y, pressure=pressure, timestamp=timestamp)

    # ── Buffer de Pixels & QImage ────────────────────────────────────────

    def get_pixel_buffer(self) -> Any:
        if self._facade:
            return self._facade.get_pixel_buffer()
        return None

    def get_qimage(self) -> Optional[QImage]:
        if self._facade:
            memview = self._facade.get_pixel_buffer()
            if memview:
                w, h = self._facade.get_width(), self._facade.get_height()
                return QImage(memview, w, h, w * 4, QImage.Format_RGBA8888)
        return None

    def dispatch(self, command: Any) -> None:
        pass
