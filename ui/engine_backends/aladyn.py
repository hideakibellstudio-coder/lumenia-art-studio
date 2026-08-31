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
from .aladyn_mdi_mixin import AladynMdiMixin
from .aladyn_geometry_mixin import AladynGeometryMixin

logger = logging.getLogger(__name__)


class AladynBackend(AladynMdiMixin, AladynSelectionMixin, AladynTransformMixin, AladynGeometryMixin, EngineBackend):
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
        self.__init_mdi__()

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
            from ui.core.document.manager import DocumentManager
            active_doc = DocumentManager.instance().active_document()
            uid = active_doc.uid if active_doc else "default_doc"
            self.set_active_document_context(uid, self._width, self._height)
            logger.info(f"[AladynBackend] Contexto C++ inicializado para doc '{uid}' ({self._width}x{self._height}).")
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

    def get_telemetry_snapshot(self):
        if self._facade and hasattr(self._facade, "get_telemetry_snapshot"):
            return self._facade.get_telemetry_snapshot()
        return None

    def reset_telemetry(self) -> None:
        if self._facade and hasattr(self._facade, "reset_telemetry"):
            self._facade.reset_telemetry()

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
                    "Normal": 0, "Multiply": 1, "Multiplicação": 1, "Screen": 2, "Divisão": 2,
                    "Overlay": 3, "Sobreposição": 3, "Darken": 4, "Escurecer": 4, "Lighten": 5, "Clarear": 5,
                    "Erase": 6, "Borracha": 6, "Pass-Through": 7, "Atravessar": 7, "PassThrough": 7,
                    "ColorDodge": 8, "Color Dodge": 8, "Subexposição (Dodge)": 8, "Subexposição": 8,
                    "ColorBurn": 9, "Color Burn": 9, "Superexposição (Burn)": 9, "Superexposição": 9,
                    "Difference": 10, "Diferença": 10, "Exclusion": 11, "Exclusão": 11,
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

    def add_layer(self, name: str = "") -> int:
        if self._facade:
            return self._facade.add_layer(name)
        return -1

    def remove_layer(self, index: int) -> bool:
        if self._facade:
            return self._facade.remove_layer(index)
        return False

    def select_layer(self, index: int) -> bool:
        if self._facade:
            return self._facade.select_layer(index)
        return False

    def set_layer_opacity(self, index: int, opacity: float) -> None:
        if self._facade:
            self._facade.set_layer_opacity(index, float(opacity))

    def set_layer_visibility(self, index: int, visible: bool) -> None:
        if self._facade:
            self._facade.set_layer_visibility(index, bool(visible))

    def set_layer_lock(self, index: int, locked: bool) -> None:
        if self._facade:
            self._facade.set_layer_lock(index, bool(locked))

    def is_layer_alpha_locked(self, index: int) -> bool:
        if self._facade and hasattr(self._facade, "is_layer_alpha_locked"):
            return self._facade.is_layer_alpha_locked(index)
        return False

    def is_layer_clipping_mask(self, index: int) -> bool:
        if self._facade and hasattr(self._facade, "is_layer_clipping_mask"):
            return self._facade.is_layer_clipping_mask(index)
        return False

    def get_active_layer_index(self) -> int:
        if self._facade and hasattr(self._facade, "get_active_layer_index"):
            return self._facade.get_active_layer_index()
        return 0

    def get_drawing_layer_count(self) -> int:
        if self._facade and hasattr(self._facade, "get_drawing_layer_count"):
            return self._facade.get_drawing_layer_count()
        return 1

    def get_layer_thumbnail_buffer(self, layer_index: int, thumb_w: int, thumb_h: int) -> Optional[bytes]:
        if self._facade and hasattr(self._facade, "get_layer_thumbnail_buffer"):
            raw = self._facade.get_layer_thumbnail_buffer(int(layer_index), int(thumb_w), int(thumb_h))
            return bytes(raw) if raw else None
        return None

    def set_undo_memory_limit_mb(self, mb: int) -> None:
        if self._facade and hasattr(self._facade, "set_undo_memory_limit_mb"):
            self._facade.set_undo_memory_limit_mb(int(mb))

    def set_undo_max_steps(self, steps: int) -> None:
        if self._facade and hasattr(self._facade, "set_undo_max_steps"):
            self._facade.set_undo_max_steps(int(steps))

    def set_canvas_paper_state(self, color: Any, visible: bool, preset_id: int = 0, enabled: bool = False) -> None:
        if self._facade and hasattr(self._facade, "get_canvas_texture"):
            c_tex = self._facade.get_canvas_texture()
            if c_tex:
                c_tex.canvas_grain_enabled = bool(enabled)
            if hasattr(self._facade, "set_canvas_height_preset"):
                self._facade.set_canvas_height_preset(int(preset_id))
            if hasattr(color, "red") and hasattr(self._facade, "set_background_color"):
                self._facade.set_background_color(color.red(), color.green(), color.blue(), 255 if visible else 0)

    def set_canvas_grain_enabled(self, enabled: bool) -> None:
        if self._facade and hasattr(self._facade, "get_canvas_texture"):
            c_tex = self._facade.get_canvas_texture()
            if c_tex:
                c_tex.canvas_grain_enabled = bool(enabled)

    def set_canvas_height_preset(self, preset_id: int) -> None:
        if self._facade and hasattr(self._facade, "set_canvas_height_preset"):
            self._facade.set_canvas_height_preset(int(preset_id))

    def set_canvas_grain_contrast(self, contrast: float) -> None:
        if self._facade and hasattr(self._facade, "get_canvas_texture"):
            c_tex = self._facade.get_canvas_texture()
            if c_tex:
                c_tex.canvas_grain_contrast = float(contrast)

    def set_canvas_grain_scale(self, scale: float) -> None:
        if self._facade and hasattr(self._facade, "get_canvas_texture"):
            c_tex = self._facade.get_canvas_texture()
            if c_tex:
                c_tex.canvas_grain_scale = float(scale)

    def set_canvas_grain_invert(self, invert: bool) -> None:
        if self._facade and hasattr(self._facade, "get_canvas_texture"):
            c_tex = self._facade.get_canvas_texture()
            if c_tex:
                c_tex.canvas_grain_invert = bool(invert)

    def set_brush_param(self, group: str, param: str, value: Any) -> None:
        if not self._facade:
            return
        prof = self._facade.get_brush_profile()
        if not prof:
            return
        if group == "root" or not group:
            if hasattr(prof, param):
                setattr(prof, param, value)
        elif group == "tip" and hasattr(prof, "tip"):
            if hasattr(prof.tip, param):
                setattr(prof.tip, param, value)
        elif group == "dynamics" and hasattr(prof, "dynamics"):
            if hasattr(prof.dynamics, param):
                setattr(prof.dynamics, param, value)
        elif group == "pencil" and hasattr(prof, "pencil_params"):
            if hasattr(prof.pencil_params, param):
                setattr(prof.pencil_params, param, value)
        elif group == "inker" and hasattr(prof, "inker_params"):
            if hasattr(prof.inker_params, param):
                setattr(prof.inker_params, param, value)
        elif group == "marker" and hasattr(prof, "marker_params"):
            if hasattr(prof.marker_params, param):
                setattr(prof.marker_params, param, value)
        elif group == "blur" and hasattr(prof, "blur_params"):
            if hasattr(prof.blur_params, param):
                setattr(prof.blur_params, param, value)
        elif group == "smudge" and hasattr(prof, "smudge_params"):
            if hasattr(prof.smudge_params, param):
                setattr(prof.smudge_params, param, value)
        elif group == "watercolor" and hasattr(prof, "watercolor_params"):
            if hasattr(prof.watercolor_params, param):
                setattr(prof.watercolor_params, param, value)
        elif group == "oil" and hasattr(prof, "oil_params"):
            if hasattr(prof.oil_params, param):
                setattr(prof.oil_params, param, value)

    def get_brush_profile_dict(self) -> dict:
        if not self._facade:
            return {}
        prof = self._facade.get_brush_profile()
        if not prof:
            return {}
        data = {
            "brush_size": getattr(prof, "brush_size", 20.0),
            "opacity": getattr(prof, "opacity", 1.0),
            "hardness": getattr(prof, "hardness", 0.85),
            "spacing_factor": getattr(prof, "spacing_factor", 0.08),
            "scatter_count": getattr(prof, "scatter_count", 1),
            "scatter_radius": getattr(prof, "scatter_radius", 0.0),
            "brush_grain_enabled": getattr(prof, "brush_grain_enabled", False),
            "brush_grain_contrast": getattr(prof, "brush_grain_contrast", 1.0),
            "brush_grain_scale": getattr(prof, "brush_grain_scale", 1.0),
            "brush_grain_invert": getattr(prof, "brush_grain_invert", False),
            "pressure_size_enabled": getattr(prof, "pressure_size_enabled", True),
            "pressure_flow_enabled": getattr(prof, "pressure_flow_enabled", True),
            "min_size_percent": getattr(prof, "min_size_percent", 0.0),
            "min_opacity_percent": getattr(prof, "min_opacity_percent", 0.0),
        }
        if hasattr(prof, "tip"):
            data.update({
                "tip_aspect": getattr(prof.tip, "aspect_ratio", 1.0),
                "tip_angle": getattr(prof.tip, "angle", 0.0),
                "follow_stroke": getattr(prof.tip, "follow_stroke", False),
            })
        if hasattr(prof, "dynamics"):
            data.update({
                "jitter_size": getattr(prof.dynamics, "jitter_size", 0.0),
                "jitter_angle": getattr(prof.dynamics, "jitter_angle", 0.0),
                "jitter_opacity": getattr(prof.dynamics, "jitter_opacity", 0.0),
                "jitter_position": getattr(prof.dynamics, "jitter_position", 0.0),
            })
        if hasattr(prof, "pencil_params"):
            data.update({
                "pencil_graphite_hardness": getattr(prof.pencil_params, "graphite_hardness", 0.5),
                "pencil_tilt_shading": getattr(prof.pencil_params, "tilt_shading_enabled", False),
            })
        if hasattr(prof, "inker_params"):
            data.update({
                "inker_flow_rate": getattr(prof.inker_params, "ink_flow_rate", 0.8),
                "inker_taper_smoothing": getattr(prof.inker_params, "taper_smoothing", 0.3),
            })
        if hasattr(prof, "marker_params"):
            data.update({
                "marker_solvent_wetness": getattr(prof.marker_params, "solvent_wetness", 0.5),
                "marker_edge_darkening": getattr(prof.marker_params, "edge_darkening", 0.4),
            })
        if hasattr(prof, "blur_params"):
            data.update({
                "blur_radius": getattr(prof.blur_params, "blur_radius", 5),
                "blur_strength": getattr(prof.blur_params, "blur_strength", 0.5),
            })
        if hasattr(prof, "smudge_params"):
            data.update({
                "smudge_color_pickup": getattr(prof.smudge_params, "color_pickup", 0.7),
                "smudge_mix_ratio": getattr(prof.smudge_params, "mix_ratio", 0.5),
                "smudge_stretch": getattr(prof.smudge_params, "smudge_stretch", 0.8),
            })
        if hasattr(prof, "watercolor_params"):
            data.update({
                "watercolor_water_level": getattr(prof.watercolor_params, "water_level", 0.5),
                "watercolor_pigment_bleed": getattr(prof.watercolor_params, "pigment_bleed", 0.5),
                "watercolor_fringe_intensity": getattr(prof.watercolor_params, "fringe_intensity", 0.4),
                "watercolor_granulation": getattr(prof.watercolor_params, "granulation", 0.3),
            })
        if hasattr(prof, "oil_params"):
            data.update({
                "oil_impasto_depth": getattr(prof.oil_params, "impasto_depth", 0.7),
                "oil_bristle_grooves": getattr(prof.oil_params, "bristle_grooves", 0.5),
                "oil_viscosity": getattr(prof.oil_params, "viscosity", 0.6),
                "oil_specular_brilliance": getattr(prof.oil_params, "specular_brilliance", 0.5),
            })
        return data

    def apply_brush_preset_dict(self, data: dict) -> None:
        if not data:
            return
        if "engine_type" in data:
            self.set_engine_type(int(data["engine_type"]))
        if "brush_size" in data:
            self.set_brush_size(float(data["brush_size"]))
        if "opacity" in data:
            self.set_brush_opacity(float(data["opacity"]))
        if "spacing_factor" in data:
            self.set_brush_spacing(float(data["spacing_factor"]))
        if "hardness" in data:
            self.set_brush_hardness(float(data["hardness"]))
        if "brush_grain_enabled" in data:
            self.set_brush_grain_enabled(bool(data["brush_grain_enabled"]))
        if "brush_height_preset" in data:
            self.set_brush_height_preset(int(data["brush_height_preset"]))
        if "brush_grain_contrast" in data:
            self.set_brush_grain_contrast(float(data["brush_grain_contrast"]))
        if "brush_grain_scale" in data:
            self.set_brush_grain_scale(float(data["brush_grain_scale"]))
        if "brush_grain_invert" in data:
            self.set_brush_invert_height(bool(data["brush_grain_invert"]))
        if "shape_preset" in data:
            self.set_shape_preset(int(data["shape_preset"]))

        key_mappings = {
            "tip_aspect": ("tip", "aspect_ratio"),
            "tip_angle": ("tip", "angle"),
            "follow_stroke": ("tip", "follow_stroke"),
            "scatter_count": ("root", "scatter_count"),
            "scatter_radius": ("root", "scatter_radius"),
            "jitter_size": ("dynamics", "jitter_size"),
            "jitter_angle": ("dynamics", "jitter_angle"),
            "jitter_opacity": ("dynamics", "jitter_opacity"),
            "jitter_position": ("dynamics", "jitter_position"),
            "pencil_graphite_hardness": ("pencil", "graphite_hardness"),
            "pencil_tilt_shading": ("pencil", "tilt_shading_enabled"),
            "inker_flow_rate": ("inker", "ink_flow_rate"),
            "inker_taper_smoothing": ("inker", "taper_smoothing"),
            "marker_solvent_wetness": ("marker", "solvent_wetness"),
            "marker_edge_darkening": ("marker", "edge_darkening"),
            "blur_radius": ("blur", "blur_radius"),
            "blur_strength": ("blur", "blur_strength"),
            "smudge_color_pickup": ("smudge", "color_pickup"),
            "smudge_mix_ratio": ("smudge", "mix_ratio"),
            "smudge_stretch": ("smudge", "smudge_stretch"),
            "watercolor_water_level": ("watercolor", "water_level"),
            "watercolor_pigment_bleed": ("watercolor", "pigment_bleed"),
            "watercolor_fringe_intensity": ("watercolor", "fringe_intensity"),
            "watercolor_granulation": ("watercolor", "granulation"),
            "oil_impasto_depth": ("oil", "impasto_depth"),
            "oil_bristle_grooves": ("oil", "bristle_grooves"),
            "oil_viscosity": ("oil", "viscosity"),
            "oil_specular_brilliance": ("oil", "specular_brilliance"),
        }
        for k, (grp, prop) in key_mappings.items():
            if k in data:
                self.set_brush_param(grp, prop, data[k])

    # ── Buffers de Prévia (Shape / Altura / Traço) ─────────────────────────

    def render_brush_preview(self, width: int, height: int, brush_state: Optional[dict] = None) -> Optional[bytes]:
        if not self._native or not hasattr(self._native, "render_stroke_preview"):
            return None
        try:
            prof = self._facade.get_brush_profile() if self._facade else self._native.BrushProfile()
            if brush_state:
                if "size" in brush_state: prof.brush_size = float(brush_state["size"])
                if "opacity" in brush_state: prof.opacity = float(brush_state["opacity"])
                if "hardness" in brush_state: prof.hardness = float(brush_state["hardness"])
                if "spacing" in brush_state: prof.spacing_factor = max(0.01, float(brush_state["spacing"]))
                if "color" in brush_state:
                    c = brush_state["color"]
                    r = int(c[0] * 255) if isinstance(c[0], float) else int(c[0])
                    g = int(c[1] * 255) if isinstance(c[1], float) else int(c[1])
                    b = int(c[2] * 255) if isinstance(c[2], float) else int(c[2])
                    prof.base_color = self._native.ColorRGBA(r, g, b, 255)
                if "watercolor_params" in brush_state and brush_state["watercolor_params"]:
                    for k, v in brush_state["watercolor_params"].items():
                        if hasattr(prof.watercolor_params, k):
                            setattr(prof.watercolor_params, k, v)
                if "oil_params" in brush_state and brush_state["oil_params"]:
                    for k, v in brush_state["oil_params"].items():
                        if hasattr(prof.oil_params, k):
                            setattr(prof.oil_params, k, v)
                if "pencil_params" in brush_state and brush_state["pencil_params"]:
                    for k, v in brush_state["pencil_params"].items():
                        if hasattr(prof.pencil_params, k):
                            setattr(prof.pencil_params, k, v)

            raw = self._native.render_stroke_preview(prof, int(width), int(height))
            return bytes(raw) if raw else None
        except Exception as e:
            logger.debug(f"[AladynBackend] render_brush_preview failed: {e}")
            return None

    def get_shape_preview_buffer(self) -> Optional[bytes]:
        if self._facade and hasattr(self._facade, "get_shape_preview_buffer"):
            raw = self._facade.get_shape_preview_buffer()
            return bytes(raw) if raw else None
        return None

    def get_shape_preview_dimensions(self) -> tuple[int, int]:
        if self._facade and hasattr(self._facade, "get_shape_preview_dimensions"):
            return self._facade.get_shape_preview_dimensions()
        return (0, 0)

    def get_brush_height_preview_buffer(self) -> Optional[bytes]:
        if self._facade and hasattr(self._facade, "get_brush_height_preview_buffer"):
            raw = self._facade.get_brush_height_preview_buffer()
            return bytes(raw) if raw else None
        return None

    def get_brush_height_preview_dimensions(self) -> tuple[int, int]:
        if self._facade and hasattr(self._facade, "get_brush_height_preview_dimensions"):
            return self._facade.get_brush_height_preview_dimensions()
        return (0, 0)

    def get_canvas_height_preview_buffer(self) -> Optional[bytes]:
        if self._facade and hasattr(self._facade, "get_canvas_height_preview_buffer"):
            raw = self._facade.get_canvas_height_preview_buffer()
            return bytes(raw) if raw else None
        return None

    def get_canvas_height_preview_dimensions(self) -> tuple[int, int]:
        if self._facade and hasattr(self._facade, "get_canvas_height_preview_dimensions"):
            return self._facade.get_canvas_height_preview_dimensions()
        return (0, 0)

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
        if self._facade: self._facade.get_brush_profile().opacity = float(opacity)

    def set_brush_spacing(self, spacing: float) -> None:
        if self._facade: self._facade.get_brush_profile().spacing_factor = float(spacing)

    def set_stabilizer_weight(self, weight: float) -> None:
        if self._facade: self._facade.get_stabilizer().set_stabilization_percentage(float(weight * 100.0 if weight <= 1.0 else weight))

    def set_brush_contrast(self, contrast: float) -> None:
        if self._facade:
            prof = self._facade.get_brush_profile()
            prof.brush_grain_contrast = float(contrast)
            if contrast <= 1.0:
                prof.hardness = float(contrast)

    def set_brush_hardness(self, hardness: float) -> None:
        if self._facade:
            self._facade.get_brush_profile().hardness = float(hardness)

    def set_brush_grain_enabled(self, enabled: bool) -> None:
        if self._facade:
            self._facade.get_brush_profile().brush_grain_enabled = bool(enabled)

    def set_brush_grain_contrast(self, contrast: float) -> None:
        if self._facade:
            self._facade.get_brush_profile().brush_grain_contrast = float(contrast)

    def set_brush_grain_scale(self, scale: float) -> None:
        if self._facade:
            self._facade.get_brush_profile().brush_grain_scale = float(scale)

    def set_brush_grain_invert(self, invert: bool) -> None:
        if self._facade:
            self._facade.get_brush_profile().brush_grain_invert = bool(invert)

    def set_brush_height_preset(self, preset_id: int) -> None:
        if self._facade and hasattr(self._facade, "set_brush_height_preset"):
            self._facade.set_brush_height_preset(int(preset_id))

    def set_shape_preset(self, preset_id: int) -> None:
        if self._facade and hasattr(self._facade, "set_shape_preset"):
            self._facade.set_shape_preset(int(preset_id))

    def set_brush_pressure(self, pressure: float) -> None:
        if self._facade:
            self._facade.get_brush_profile().pressure_size_enabled = bool(pressure > 0.0)

    def set_brush_invert_height(self, invert: bool) -> None:
        if self._facade:
            self._facade.get_brush_profile().brush_grain_invert = bool(invert)

    def set_pressure_curve_power(self, power: float) -> None:
        pass

    def set_curve_control_points(self, curve_type: str, points: list[tuple[float, float]], enabled: bool) -> None:
        if not self._facade:
            return
        prof = self._facade.get_brush_profile()
        if not prof:
            return

        if curve_type == "pressure_size":
            prof.pressure_size_enabled = bool(enabled)
            if self._native and len(points) == 4:
                prof.pressure_size_curve.set_control_points(
                    self._native.Point2D(points[0][0], points[0][1]),
                    self._native.Point2D(points[1][0], points[1][1]),
                    self._native.Point2D(points[2][0], points[2][1]),
                    self._native.Point2D(points[3][0], points[3][1]),
                )
        elif curve_type == "pressure_flow":
            prof.pressure_flow_enabled = bool(enabled)
            if self._native and len(points) == 4:
                prof.pressure_flow_curve.set_control_points(
                    self._native.Point2D(points[0][0], points[0][1]),
                    self._native.Point2D(points[1][0], points[1][1]),
                    self._native.Point2D(points[2][0], points[2][1]),
                    self._native.Point2D(points[3][0], points[3][1]),
                )
        elif curve_type == "velocity_size":
            prof.velocity_size_enabled = bool(enabled)
            if self._native and len(points) == 4:
                prof.velocity_size_curve.set_control_points(
                    self._native.Point2D(points[0][0], points[0][1]),
                    self._native.Point2D(points[1][0], points[1][1]),
                    self._native.Point2D(points[2][0], points[2][1]),
                    self._native.Point2D(points[3][0], points[3][1]),
                )

    def set_min_density_active(self, active: bool) -> None:
        if self._facade:
            self._facade.get_brush_profile().pressure_flow_enabled = bool(active)

    def set_min_density_value(self, value: float) -> None:
        if self._facade:
            val = float(value / 100.0 if value > 1.0 else value)
            self._facade.get_brush_profile().min_size_percent = val
            self._facade.get_brush_profile().min_opacity_percent = val

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
        self, seed_x: int, seed_y: int, fill_color: QtGui.QColor, tolerance: int = 20,
        contiguous: bool = True, expand_px: int = 1, gap_closing_px: int = 0,
        aa: bool = True, sample_all: bool = True,
    ) -> bool:
        """Executa Flood Fill ultra-rápido (<1ms) diretamente no motor nativo C++."""
        if not self._facade or not self._native or not hasattr(self._facade, "flood_fill"):
            return False
        native_color = self._native.ColorRGBA(
            int(fill_color.red()), int(fill_color.green()), int(fill_color.blue()), int(fill_color.alpha())
        )
        return self._facade.flood_fill(
            int(seed_x), int(seed_y), native_color, int(tolerance), bool(contiguous),
            int(expand_px), int(gap_closing_px), bool(aa), bool(sample_all)
        )

    def set_undo_memory_limit_mb(self, mb: int) -> None:
        self._undo_memory_limit_mb = int(mb)
        if self._facade and hasattr(self._facade, "set_undo_memory_limit_mb"):
            self._facade.set_undo_memory_limit_mb(int(mb))
        # Aplica em todas as facades ativas
        if hasattr(self, "_doc_facades"):
            for fac in self._doc_facades.values():
                if hasattr(fac, "set_undo_memory_limit_mb"):
                    fac.set_undo_memory_limit_mb(int(mb))

    def get_undo_memory_limit_mb(self) -> int:
        if self._facade and hasattr(self._facade, "get_undo_memory_limit_mb"):
            return self._facade.get_undo_memory_limit_mb()
        return getattr(self, "_undo_memory_limit_mb", 256)

    def set_undo_max_steps(self, steps: int) -> None:
        self._undo_max_steps = int(steps)
        if self._facade and hasattr(self._facade, "set_undo_max_steps"):
            self._facade.set_undo_max_steps(int(steps))
        if hasattr(self, "_doc_facades"):
            for fac in self._doc_facades.values():
                if hasattr(fac, "set_undo_max_steps"):
                    fac.set_undo_max_steps(int(steps))

    def get_undo_max_steps(self) -> int:
        if self._facade and hasattr(self._facade, "get_undo_max_steps"):
            return self._facade.get_undo_max_steps()
        return getattr(self, "_undo_max_steps", 50)

    def dispatch(self, command: Any) -> None:
        pass
