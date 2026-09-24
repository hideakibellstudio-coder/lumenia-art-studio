"""
BridgeClient — Fachada Engine-Agnóstica da Casca
==================================================
A casca nunca fala diretamente com o motor. O BridgeClient é a fachada que
encaminha operações para o `EngineBackend` ativo registrado no
`EngineRegistry` (plugado por um plugin de sistema no boot).

Sem backends registrados (ex.: engenho arquivado), o modo casca pura é
absolutamente seguro: renderer == None, canvas vazio, sem crashes.
"""

import logging
from dataclasses import dataclass

from ui.core.engine.registry import EngineRegistry

logger = logging.getLogger(__name__)


@dataclass
class BridgePointerEvent:
    """Ponto final convertido para o espaço do canvas (interface legada)."""

    x: float
    y: float
    pressure: float
    timestamp: float


class BridgeClient:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._backend = None  # cache lazy do backend ativo (EngineRegistry)

    # ── Resolução do backend ─────────────────────────────────────────────

    @property
    def backend(self):
        """Retorna o EngineBackend ativo, ou None se a casca estiver sem motor."""
        if self._backend is None:
            self._backend = EngineRegistry.instance().get_backend()
        return self._backend

    # ── Compatibilidade legada ───────────────────────────────────────────

    @property
    def renderer(self):
        """Backend ativo (None em modo casca pura). Canvas usa como 'engine ready'."""
        return self.backend

    @property
    def input_adapter(self):
        """Transformação de viewport do backend (None em modo casca pura)."""
        return self.backend

    # ── Ciclo de vida ────────────────────────────────────────────────────

    def init_renderer(self, hwnd: int, width: int, height: int, canvas_w: int, canvas_h: int):
        backend = self.backend
        if backend is None:
            logger.debug("[BridgeClient] Nenhum backend de motor ativo — canvas vazio (casca pura).")
            return
        backend.init_renderer(hwnd, width, height, canvas_w, canvas_h)

    def resize_renderer(self, width: int, height: int):
        if self.backend:
            self.backend.resize(width, height)
        else:
            logger.debug("[BridgeClient] resize_renderer ignorado — sem motor.")

    def resize(self, width: int, height: int):
        self.resize_renderer(width, height)

    def update_view(self, zoom: float, pan_x: float, pan_y: float, rotation: float):
        if self.backend:
            self.backend.update_view(zoom, pan_x, pan_y, rotation)

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> BridgePointerEvent:
        backend = self.backend
        if backend is None:
            return BridgePointerEvent(x=screen_x, y=screen_y, pressure=pressure, timestamp=timestamp)
        evt = backend.to_canvas(screen_x, screen_y, pressure, timestamp)
        return BridgePointerEvent(x=evt.x, y=evt.y, pressure=evt.pressure, timestamp=evt.timestamp)

    # ── Framebuffer ──────────────────────────────────────────────────────

    def render(self, pan_x: float, pan_y: float, zoom: float, rotation_rad: float):
        if self.backend:
            self.backend.render(pan_x, pan_y, zoom, rotation_rad)

    # ── Traço ────────────────────────────────────────────────────────────

    def start_stroke(self, x: float, y: float, pressure: float):
        if self.backend:
            self.backend.start_stroke(x, y, pressure)

    def paint_stroke(self, x: float, y: float, pressure: float):
        if self.backend:
            self.backend.paint_stroke(x, y, pressure)

    def end_stroke(self):
        if self.backend:
            self.backend.end_stroke()

    def clear_canvas(self):
        if self.backend:
            self.backend.clear_canvas()

    # ── Pincel ───────────────────────────────────────────────────────────

    def set_brush_color(self, r: float, g: float, b: float):
        if self.backend:
            self.backend.set_brush_color(r, g, b)

    def set_brush_size(self, size: float):
        if self.backend:
            self.backend.set_brush_size(size)

    def set_brush_pressure(self, pressure: float):
        if self.backend:
            self.backend.set_brush_pressure(pressure)

    def set_brush_contrast(self, contrast: float):
        if self.backend:
            self.backend.set_brush_contrast(contrast)

    def set_brush_invert_height(self, invert: bool):
        if self.backend:
            self.backend.set_brush_invert_height(invert)

    def set_pressure_curve_power(self, power: float):
        if self.backend:
            self.backend.set_pressure_curve_power(power)

    def set_brush_spacing(self, spacing: float):
        if self.backend:
            self.backend.set_brush_spacing(spacing)

    def set_brush_opacity(self, opacity: float):
        if self.backend:
            self.backend.set_brush_opacity(opacity)

    def set_stabilizer_weight(self, weight: float):
        if self.backend:
            self.backend.set_stabilizer_weight(weight)

    def set_min_density_active(self, active: bool):
        if self.backend:
            self.backend.set_min_density_active(active)

    def set_min_density_value(self, value: float):
        if self.backend:
            self.backend.set_min_density_value(value)

    # ── Texturas ─────────────────────────────────────────────────────────

    def set_shape_texture(self, pixels: bytes, width: int, height: int):
        if self.backend:
            self.backend.set_shape_texture(pixels, width, height)

    def set_heightmap_texture(self, pixels: bytes, width: int, height: int):
        if self.backend:
            self.backend.set_heightmap_texture(pixels, width, height)
