"""
WgpuRustBackend — Adaptador do Motor Legado WGPU/Rust (engine_core)
====================================================================
ÚNICO módulo da casca autorizado a importar `engine_core` (o binário PyO3
compilado a partir do motor Rust arquivado em `archive/rust-engine/`).

O motor é carregado LAZY: se o `.pyd` não estiver presente no ambiente, o
backend fica com `available == False` e a interface roda em modo casca pura
(canvas vazio), exatamente como desejado.

Histórico: traduz o antigo client/dispatcher (que importavam engine_core)
para o contrato `EngineBackend`. Motor futuro = nova classe em ui/engine_backends.
"""

from __future__ import annotations

import logging
from typing import Any

from ui.core.engine.backend import EngineBackend, PointerEvent

logger = logging.getLogger(__name__)


class WgpuRustBackend(EngineBackend):
    """Backend que fala com o binário `engine_core` (PyRenderer + EngineDispatcher)."""

    name = "wgpu_rust"

    def __init__(self) -> None:
        self._engine: Any = None
        self._renderer: Any = None
        self._input_adapter: Any = None
        self._dispatcher: Any = None

        try:
            import engine_core  # import lazy — binário pode não existir
            self._engine = engine_core
            self._input_adapter = engine_core.InputAdapter()
            logger.info("[WgpuRustBackend] Módulo engine_core carregado com sucesso.")
        except Exception as e:
            logger.info(
                f"[WgpuRustBackend] engine_core indisponível — modo casca pura "
                f"({type(e).__name__}: {e})."
            )
            self._engine = None

    # ── Disponibilidade ──────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return self._engine is not None

    def get_capabilities(self) -> dict[str, object]:
        """Declara somente o subconjunto que o backend legado realmente executa."""
        renderer = self._renderer is not None
        return {
            "native_engine": self.available,
            "render": renderer,
            "stroke": renderer,
            "brush_controls": renderer,
            "raster_document": False,
            "multi_document": False,
            "layers": False,
            "groups": False,
            "filters": False,
            "selection": False,
            "transform": False,
            "guides": False,
            "canvas_texture": renderer,
            "history": False,
            "scratch_history": False,
            "lod": False,
            "telemetry": False,
            "low_latency": False,
            "linear_gamma": False,
            "deep_color": False,
            "color_profiles": False,
            "color_profile_preview": False,
            "embedded_icc_profiles": False,
            "rgba16_document": False,
            "export_image": False,
            "document_pixel_format": "indisponível",
        }

    # ── Ciclo de vida ────────────────────────────────────────────────────

    def init_renderer(self, hwnd: int, width: int, height: int, canvas_w: int, canvas_h: int) -> None:
        if self._engine is None:
            return
        try:
            self._renderer = self._engine.PyRenderer(hwnd, width, height, canvas_w, canvas_h)
            self._input_adapter.canvas_w = float(canvas_w)
            self._input_adapter.canvas_h = float(canvas_h)
            self._input_adapter.view_w = float(width)
            self._input_adapter.view_h = float(height)
            self._dispatcher = self._engine.EngineDispatcher()
            logger.info("[WgpuRustBackend] PyRenderer inicializado (HWND %s).", hwnd)
        except BaseException as e:  # noqa: BLE001 — PanicException do PyO3 não herda de Exception
            logger.error(
                f"[WgpuRustBackend] Falha ao inicializar PyRenderer — backend desativado "
                f"(modo casca pura): {type(e).__name__}: {e}"
            )
            self._renderer = None
            self._dispatcher = None

    def resize(self, width: int, height: int) -> None:
        if self._renderer:
            self._renderer.resize(width, height)
        if self._input_adapter is not None:
            self._input_adapter.view_w = float(width)
            self._input_adapter.view_h = float(height)

    def render(self, pan_x: float, pan_y: float, zoom: float, rotation_rad: float) -> None:
        if self._renderer:
            self._renderer.render(pan_x, pan_y, zoom, rotation_rad)

    # ── Traço ────────────────────────────────────────────────────────────

    def start_stroke(self, x: float, y: float, pressure: float) -> None:
        if self._renderer:
            self._renderer.start_stroke(x, y, pressure)

    def paint_stroke(self, x: float, y: float, pressure: float) -> None:
        if self._renderer:
            self._renderer.paint_stroke(x, y, pressure)

    def end_stroke(self) -> None:
        if self._renderer:
            self._renderer.end_stroke()

    def clear_canvas(self) -> None:
        if self._renderer:
            self._renderer.clear_canvas()

    # ── Pincel ───────────────────────────────────────────────────────────

    def set_brush_color(self, r: float, g: float, b: float) -> None:
        if self._renderer:
            self._renderer.set_brush_color(r, g, b)

    def set_brush_size(self, size: float) -> None:
        if self._renderer:
            self._renderer.set_brush_size(size)

    def set_brush_pressure(self, pressure: float) -> None:
        if self._renderer:
            self._renderer.set_brush_pressure(pressure)

    def set_brush_contrast(self, contrast: float) -> None:
        if self._renderer:
            self._renderer.set_brush_contrast(contrast)

    def set_brush_invert_height(self, invert: bool) -> None:
        if self._renderer:
            self._renderer.set_brush_invert_height(invert)

    def set_pressure_curve_power(self, power: float) -> None:
        if self._renderer:
            self._renderer.set_pressure_curve_power(power)

    def set_brush_spacing(self, spacing: float) -> None:
        if self._renderer:
            self._renderer.set_brush_spacing(spacing)

    def set_brush_opacity(self, opacity: float) -> None:
        if self._renderer:
            self._renderer.set_brush_opacity(opacity)

    def set_stabilizer_weight(self, weight: float) -> None:
        if self._renderer:
            self._renderer.set_stabilizer_weight(weight)

    def set_min_density_active(self, active: bool) -> None:
        if self._renderer:
            self._renderer.set_min_density_active(active)

    def set_min_density_value(self, value: float) -> None:
        if self._renderer:
            self._renderer.set_min_density_value(value)

    # ── Texturas (shape / heightmap) ─────────────────────────────────────

    def set_shape_texture(self, pixels: bytes, width: int, height: int) -> None:
        if self._renderer:
            self._renderer.set_shape_texture(pixels, width, height)

    def set_heightmap_texture(self, pixels: bytes, width: int, height: int) -> None:
        if self._renderer:
            self._renderer.set_heightmap_texture(pixels, width, height)

    # ── Viewport / Câmera ────────────────────────────────────────────────

    def update_view(self, zoom: float, pan_x: float, pan_y: float, rotation: float) -> None:
        if self._input_adapter is not None:
            self._input_adapter.update_view(zoom, pan_x, pan_y, rotation)

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> PointerEvent:
        if self._input_adapter is None:
            return PointerEvent(x=screen_x, y=screen_y, pressure=pressure, timestamp=timestamp)
        evt = self._input_adapter.to_canvas(screen_x, screen_y, pressure, timestamp)
        return PointerEvent(
            x=float(evt.x),
            y=float(evt.y),
            pressure=float(evt.pressure),
            timestamp=float(evt.timestamp),
        )

    # ── Despacho ─────────────────────────────────────────────────────────

    def dispatch(self, command: Any) -> None:
        if self._dispatcher is None:
            logger.debug("[WgpuRustBackend] Dispatcher não inicializado — evento descartado.")
            return
        try:
            self._dispatcher.dispatch(command)
        except Exception as e:
            logger.error(f"[WgpuRustBackend] Erro ao despachar evento para o motor: {e}")
