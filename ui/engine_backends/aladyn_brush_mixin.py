"""
AladynBrushMixin — Mapeamento Atômico de Perfis, Presets e Parâmetros de Pincéis para o AladynBackend.
========================================================================================================
Isola a manipulação de parâmetros por motor (Pencil, Inker, Marker, Oil, Watercolor, Smudge, Blur),
curvas de dinâmica Bezier LUT, texturas de ponta/papel e geração de buffers de prévia do pincel.
"""

from __future__ import annotations
import logging
from typing import Any, Optional, TYPE_CHECKING

from .native_fallback import nativo_tem

if TYPE_CHECKING:
    from aladyn_engine_native import BrushProfile, CanvasTexture

logger = logging.getLogger(__name__)


class AladynBrushMixin:
    """Mixin responsável pelo perfil, presets e parâmetros de pincéis no AladynBackend."""

    def set_canvas_paper_state(self, color: Any, visible: bool, preset_id: int = 0, enabled: bool = False, *, reset_texture: bool = True) -> None:
        if self._facade:
            c_tex: "CanvasTexture" = self._facade.get_canvas_texture()
            if c_tex:
                c_tex.canvas_grain_enabled = bool(enabled)
            if reset_texture:
                self._facade.set_canvas_height_preset(int(preset_id))
            if hasattr(color, "red"):
                self._facade.set_background_color(int(color.red()), int(color.green()), int(color.blue()), int(color.alpha() if visible else 0))
            elif isinstance(color, (tuple, list)) and len(color) >= 3:
                a = int(color[3]) if len(color) > 3 and visible else (255 if visible else 0)
                self._facade.set_background_color(int(color[0]), int(color[1]), int(color[2]), a)

    def set_canvas_height_preset(self, preset_id: int) -> None:
        if self._facade:
            self._facade.set_canvas_height_preset(int(preset_id))

    def set_canvas_grain_contrast(self, contrast: float) -> None:
        if self._facade:
            c_tex: "CanvasTexture" = self._facade.get_canvas_texture()
            if c_tex:
                c_tex.canvas_grain_contrast = float(contrast)
                c_tex.invalidate_lut()

    def set_canvas_grain_scale(self, scale: float) -> None:
        if self._facade:
            c_tex: "CanvasTexture" = self._facade.get_canvas_texture()
            if c_tex:
                c_tex.canvas_grain_scale = float(scale)

    def set_canvas_grain_invert(self, invert: bool) -> None:
        if self._facade:
            c_tex: "CanvasTexture" = self._facade.get_canvas_texture()
            if c_tex:
                c_tex.canvas_grain_invert = bool(invert)
                c_tex.invalidate_lut()

    def set_brush_param(self, group: str, param: str, value: Any) -> None:
        """Escreve um campo do BrushProfile resolvido pela tabela de parâmetros.

        Lança KeyError quando o par (grupo, parâmetro) não é declarado em
        `brush_param_table.TABELA`. A versão anterior descartava em silêncio —
        era uma cadeia de `if hasattr(...)` sem `else` — e foi assim que dois
        sliders de jitter passaram meses escrevendo num grupo 'dynamics' que
        nunca existiu no módulo nativo, sem um único erro visível.

        A resolução acontece ANTES da checagem do facade, de propósito: um par
        inválido é erro de programação e deve falhar mesmo sem documento aberto.
        """
        from .brush_param_table import alvo_nativo, resolver

        linha = resolver(group, param)
        if not self._facade:
            return
        prof: "BrushProfile" = self._facade.get_brush_profile()
        if not prof:
            return
        destino = alvo_nativo(prof, linha.grupo)
        setattr(destino, linha.atributo, linha.para_motor(value, self._native))

    def get_brush_profile_dict(self) -> dict:
        from .aladyn_brush_profiles import get_brush_profile_dict
        return get_brush_profile_dict(self._facade)

    def apply_brush_preset_dict(self, data: dict) -> None:
        from .aladyn_brush_profiles import apply_brush_preset_dict
        apply_brush_preset_dict(self, self._facade, data)

    def render_brush_preview(self, width: int, height: int, brush_state: Optional[dict] = None) -> Optional[bytes]:
        if not self._native or not nativo_tem(self._native, "render_stroke_preview", "o painel de pincel mostra uma prévia aproximada"):
            return None
        try:
            # get_brush_profile() devolve REFERÊNCIA ao perfil vivo do documento; a
            # prévia trabalha numa cópia para nunca alterar o pincel em uso.
            prof: "BrushProfile" = (
                self._native.BrushProfile(self._facade.get_brush_profile())
                if self._facade else self._native.BrushProfile()
            )
            if brush_state:
                if "engine_type" in brush_state:
                    # O binding exige o enum nativo; um int puro levanta TypeError
                    # (engolido abaixo) e a prévia caía no desenho vetorial.
                    prof.engine_type = self._native.EngineType(int(brush_state["engine_type"]))
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
                for group in (
                    "watercolor_params", "oil_params", "pencil_params",
                    "inker_params", "marker_params", "blur_params", "smudge_params"
                ):
                    if group in brush_state and brush_state[group] and hasattr(prof, group):
                        sub_obj = getattr(prof, group)
                        for k, v in brush_state[group].items():
                            if hasattr(sub_obj, k):
                                setattr(sub_obj, k, v)

            raw = self._native.render_stroke_preview(prof, int(width), int(height))
            return bytes(raw) if raw else None
        except Exception as e:
            logger.debug(f"[AladynBackend] render_brush_preview failed: {e}")
            return None

    def get_shape_preview_buffer(self) -> Optional[bytes]:
        if self._facade:
            raw = self._facade.get_shape_preview_buffer()
            return bytes(raw) if raw else None
        return None

    def get_shape_preview_dimensions(self) -> tuple[int, int]:
        if self._facade:
            return self._facade.get_shape_preview_dimensions()
        return (0, 0)

    def get_brush_height_preview_buffer(self) -> Optional[bytes]:
        if self._facade:
            raw = self._facade.get_brush_height_preview_buffer()
            return bytes(raw) if raw else None
        return None

    def get_brush_height_preview_dimensions(self) -> tuple[int, int]:
        if self._facade:
            return self._facade.get_brush_height_preview_dimensions()
        return (0, 0)

    def get_canvas_height_preview_buffer(self) -> Optional[bytes]:
        if self._facade:
            raw = self._facade.get_canvas_height_preview_buffer()
            return bytes(raw) if raw else None
        return None

    def get_canvas_height_preview_dimensions(self) -> tuple[int, int]:
        if self._facade:
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
            prof: "BrushProfile" = self._facade.get_brush_profile()
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

    def set_brush_height_preset(self, preset_id: int) -> None:
        if self._facade:
            self._facade.set_brush_height_preset(int(preset_id))

    def set_shape_preset(self, preset_id: int) -> None:
        if self._facade:
            self._facade.set_shape_preset(int(preset_id))

    def set_brush_pressure(self, pressure: float) -> None:
        if self._facade:
            self._facade.get_brush_profile().pressure_size_enabled = bool(pressure > 0.0)

    def set_brush_invert_height(self, invert: bool) -> None:
        if self._facade:
            self._facade.get_brush_profile().brush_grain_invert = bool(invert)

    def set_pressure_curve_power(self, power: float) -> None:
        import math
        power = float(power)
        if not math.isfinite(power) or power <= 0:
            raise ValueError("pressure power must be finite and positive")
        if self._facade:
            profile = self._facade.get_brush_profile()
            profile.pressure_size_curve.set_power(power)

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
            from .aladyn_buffers import texture_intensity
            self._facade.load_shape_texture(width, height, texture_intensity(pixels, width, height))

    def set_heightmap_texture(self, pixels: bytes, width: int, height: int) -> None:
        if self._facade:
            from .aladyn_buffers import texture_intensity
            self._facade.load_brush_height_texture(width, height, texture_intensity(pixels, width, height))
