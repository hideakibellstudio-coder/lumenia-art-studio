"""
AladynBrushMixin — Mapeamento Atômico de Perfis, Presets e Parâmetros de Pincéis para o AladynBackend.
========================================================================================================
Isola a manipulação de parâmetros por motor (Pencil, Inker, Marker, Oil, Watercolor, Smudge, Blur),
curvas de dinâmica Bezier LUT, texturas de ponta/papel e geração de buffers de prévia do pincel.
"""

from __future__ import annotations
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AladynBrushMixin:
    """Mixin responsável pelo perfil, presets e parâmetros de pincéis no AladynBackend."""

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
        if "stabilizer_weight" in data:
            self.set_stabilizer_weight(float(data["stabilizer_weight"]))
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
            self._facade.get_brush_profile().opacity = float(opacity)

    def set_brush_spacing(self, spacing: float) -> None:
        if self._facade:
            self._facade.get_brush_profile().spacing_factor = float(spacing)

    def set_stabilizer_weight(self, weight: float) -> None:
        if self._facade:
            self._facade.get_stabilizer().set_stabilization_percentage(float(weight * 100.0 if weight <= 1.0 else weight))

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

    def set_shape_texture(self, pixels: bytes, width: int, height: int) -> None:
        if self._facade:
            self._facade.load_shape_texture(width, height, pixels)

    def set_heightmap_texture(self, pixels: bytes, width: int, height: int) -> None:
        if self._facade:
            self._facade.load_brush_height_texture(width, height, pixels)
