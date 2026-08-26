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
from ui.core.engine.color_profiles_catalog import get_default_color_profiles
from .aladyn_selection_mixin import AladynSelectionMixin
from .aladyn_transform_mixin import AladynTransformMixin

logger = logging.getLogger(__name__)


class AladynBackend(EngineBackend, AladynSelectionMixin, AladynTransformMixin):
    """Backend nativo que encapsula a PaintEngineFacade do ALADYN ENGINE."""

    name = "aladyn"

    def __init__(self) -> None:
        self._native: Any = None
        self._facade: Any = None
        self._width: int = 800
        self._height: int = 600
        self.last_telemetry: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._action_stack: list[tuple[str, int]] = []
        self._redo_stack: list[tuple[str, int]] = []
        self._is_filling: bool = False

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
            if not getattr(self, "_is_filling", False):
                self._action_stack.append(("stroke", 1))
                self._redo_stack.clear()

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

    def set_layer_blend_mode(self, index: int, mode_val) -> None:
        if self._facade and self._native:
            if isinstance(mode_val, int):
                bm_enum = self._native.LayerBlendMode(mode_val)
            elif isinstance(mode_val, str):
                blend_map = {
                    "Normal": 0, "Multiply": 1, "Multiplicação": 1,
                    "Screen": 2, "Divisão": 2, "Overlay": 3, "Sobreposição": 3,
                    "Darken": 4, "Escurecer": 4, "Lighten": 5, "Clarear": 5,
                    "Erase": 6, "Borracha": 6, "Pass-Through": 7, "Atravessar": 7, "PassThrough": 7,
                    "ColorDodge": 8, "Color Dodge": 8, "Subexposição (Dodge)": 8, "Subexposição": 8,
                    "ColorBurn": 9, "Color Burn": 9, "Superexposição (Burn)": 9, "Superexposição": 9,
                    "Difference": 10, "Diferença": 10,
                    "Exclusion": 11, "Exclusão": 11,
                    "Add": 12, "Adicionar (Add)": 12, "Adicionar": 12
                }
                bm_enum = self._native.LayerBlendMode(blend_map.get(mode_val, 0))
            else:
                bm_enum = mode_val
            self._facade.set_layer_blend_mode(index, bm_enum)

    def reorder_layer(self, from_index: int, to_index: int) -> bool:
        if self._facade:
            return self._facade.reorder_layer(from_index, to_index)
        return False

    def reorder_layers(self, new_order: list[int]) -> bool:
        if self._facade and hasattr(self._facade, "reorder_layers"):
            return self._facade.reorder_layers(new_order)
        return False

    def set_layer_parents(self, parent_indices: list[int]) -> bool:
        if self._facade and hasattr(self._facade, "set_layer_parents"):
            return self._facade.set_layer_parents(parent_indices)
        return False

    def add_group(self, name: str = "Novo Grupo") -> int:
        if self._facade and hasattr(self._facade, "add_group"):
            return self._facade.add_group(name)
        return -1

    def add_filter_layer(self, name: str, filter_type_id: int) -> int:
        if self._facade and hasattr(self._facade, "add_filter_layer"):
            return self._facade.add_filter_layer(name, filter_type_id)
        return -1

    def set_filter_params(self, index: int, params: list[float]) -> None:
        if self._facade and hasattr(self._facade, "set_filter_params"):
            self._facade.set_filter_params(index, [float(x) for x in params])

    def get_filter_params(self, index: int) -> list[float]:
        if self._facade and hasattr(self._facade, "get_filter_params"):
            return list(self._facade.get_filter_params(index))
        return []

    def get_filter_type(self, index: int) -> int:
        if self._facade and hasattr(self._facade, "get_filter_type"):
            return self._facade.get_filter_type(index)
        return -1

    def is_filter_layer(self, index: int) -> bool:
        if self._facade and hasattr(self._facade, "is_filter_layer"):
            return self._facade.is_filter_layer(index)
        return False

    def set_layer_name(self, index: int, name: str) -> None:
        if self._facade and hasattr(self._facade, "set_layer_name"):
            self._facade.set_layer_name(index, name)

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

    def flatten_group(self, index: int) -> bool:
        if self._facade and hasattr(self._facade, "flatten_group"):
            return self._facade.flatten_group(index)
        return False

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

    def undo(self) -> bool:
        if self._facade and hasattr(self._facade, "undo"):
            return self._facade.undo()
        return False

    def redo(self) -> bool:
        if self._facade and hasattr(self._facade, "redo"):
            return self._facade.redo()
        return False

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

    def get_display_pixel_buffer(self) -> Any:
        if self._facade:
            if hasattr(self._facade, "get_display_pixel_buffer"):
                return self._facade.get_display_pixel_buffer()
            return self._facade.get_pixel_buffer()
        return None

    def get_qimage(self) -> Optional[QImage]:
        if self._facade:
            memview = self.get_display_pixel_buffer()
            if memview:
                w, h = self._facade.get_width(), self._facade.get_height()
                return QImage(memview, w, h, w * 4, QImage.Format_RGBA8888)
        return None

    # ── Amostragem de Cores (Eyedropper) ─────────────────────────────────

    def pick_color_merged(self, x: int, y: int, sample_radius: int = 0) -> tuple:
        if self._facade and hasattr(self._facade, "pick_color_merged"):
            return self._facade.pick_color_merged(int(x), int(y), int(sample_radius))
        return (0, 0, 0, 0)

    def pick_color_layer(self, layer_index: int, x: int, y: int, sample_radius: int = 0) -> tuple:
        if self._facade and hasattr(self._facade, "pick_color_layer"):
            return self._facade.pick_color_layer(int(layer_index), int(x), int(y), int(sample_radius))
        return (0, 0, 0, 0)

    # ── Gerenciamento de Perfis de Cor (Color Profiles) ───────────────────

    def set_color_profile(self, profile_id: int) -> None:
        self._color_profile_id = int(profile_id)
        if self._facade and hasattr(self._facade, "set_color_profile"):
            self._facade.set_color_profile(int(profile_id))

    def get_color_profile(self) -> int:
        if self._facade and hasattr(self._facade, "get_color_profile"):
            return self._facade.get_color_profile()
        return getattr(self, "_color_profile_id", 0)

    def get_color_profile_name(self, profile_id: int) -> str:
        profiles = self.get_available_color_profiles()
        for p in profiles:
            if p.get("id") == int(profile_id):
                return p.get("name", "Padrão (sRGB)")
        return "Padrão (sRGB)"

    def get_available_color_profiles(self) -> list[dict]:
        if self._native and hasattr(self._native, "get_available_color_profiles"):
            return self._native.get_available_color_profiles()
        return get_default_color_profiles()


    def fill_area(
        self,
        seed_x: int,
        seed_y: int,
        fill_color: QtGui.QColor,
        tolerance: int = 20,
        contiguous: bool = True,
        expand_px: int = 1,
        gap_closing_px: int = 0,
        aa: bool = True,
        sample_all: bool = True,
    ) -> bool:
        """Executa Flood Fill ultra-rápido (<1ms) diretamente no motor nativo C++."""
        if not self._facade or not self._native:
            return False

        if not hasattr(self._facade, "flood_fill"):
            return False

        native_color = self._native.ColorRGBA(
            int(fill_color.red()),
            int(fill_color.green()),
            int(fill_color.blue()),
            int(fill_color.alpha()),
        )

        return self._facade.flood_fill(
            int(seed_x),
            int(seed_y),
            native_color,
            int(tolerance),
            bool(contiguous),
            int(expand_px),
            int(gap_closing_px),
            bool(aa),
            bool(sample_all),
        )

    def set_symmetry_config(
        self,
        mode: int,
        cx: float,
        cy: float,
        angle_rad: float,
        segments: int = 6,
        stop_at_center: bool = False,
    ) -> None:
        """Configura a simetria ativa no motor nativo C++."""
        if self._facade and hasattr(self._facade, "set_symmetry_config"):
            self._facade.set_symmetry_config(
                int(mode), float(cx), float(cy), float(angle_rad), int(segments), bool(stop_at_center)
            )

    def clear_symmetry(self) -> None:
        """Desativa a simetria ativa no motor C++."""
        if self._facade and hasattr(self._facade, "clear_symmetry"):
            self._facade.clear_symmetry()

    def set_guide_config(
        self,
        guide_type: int,
        p0x: float = 0.0, p0y: float = 0.0,
        p1x: float = 100.0, p1y: float = 100.0,
        p2x: float = 200.0, p2y: float = 200.0,
        p3x: float = 300.0, p3y: float = 300.0,
        vp_ax: float = 400.0, vp_ay: float = 300.0,
        vp_bx: float = -1000.0, vp_by: float = 300.0,
        vp_cx: float = 400.0, vp_cy: float = -2000.0,
        cx: float = 0.0, cy: float = 0.0,
        fov: float = 130.0, pitch: float = 0.0, yaw: float = 0.0,
        snap_radius: float = 32.0,
    ) -> None:
        """Configura a régua / guia de perspectiva no motor nativo C++."""
        if self._facade and hasattr(self._facade, "set_guide_config"):
            self._facade.set_guide_config(
                int(guide_type),
                float(p0x), float(p0y), float(p1x), float(p1y),
                float(p2x), float(p2y), float(p3x), float(p3y),
                float(vp_ax), float(vp_ay), float(vp_bx), float(vp_by),
                float(vp_cx), float(vp_cy), float(cx), float(cy),
                float(fov), float(pitch), float(yaw), float(snap_radius)
            )

    def clear_guide(self) -> None:
        """Desativa as réguas ativas no motor C++."""
        if self._facade and hasattr(self._facade, "clear_guide"):
            self._facade.clear_guide()

    def snap_point(
        self,
        raw_x: float,
        raw_y: float,
        last_x: float = 0.0,
        last_y: float = 0.0,
        has_last: bool = False,
    ) -> tuple[float, float]:
        """Calcula atração do cursor para réguas ativas via C++."""
        if self._facade and hasattr(self._facade, "snap_point"):
            res = self._facade.snap_point(float(raw_x), float(raw_y), float(last_x), float(last_y), bool(has_last))
            if res and len(res) >= 2:
                return (float(res[0]), float(res[1]))
        return (float(raw_x), float(raw_y))

    def dispatch(self, command: Any) -> None:
        pass
