"""
AladynBrushProfiles — Serialização e Mapeamento de Parâmetros de Pincel
========================================================================
Converte entre estruturas nativas BrushProfile e dicionários de preset da UI.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # apenas para tipagem: evita ciclo de import em runtime
    from ui.core.engine.backend import EngineBackend


def get_brush_profile_dict(facade: Any) -> dict:
    if not facade:
        return {}
    prof = facade.get_brush_profile()
    if not prof:
        return {}
    stab_pct = 40.0
    if hasattr(facade, "get_stabilizer"):
        try:
            stab_pct = float(facade.get_stabilizer().get_stabilization_percentage())
        except Exception:
            stab_pct = 40.0
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
        "stroke_taper_enabled": getattr(prof, "stroke_taper_enabled", True),
        "stabilizer_weight": stab_pct / 100.0,
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


def apply_brush_preset_dict(backend: EngineBackend, facade: Any, data: dict) -> None:
    if not data:
        return
    if not hasattr(backend, "_last_brush_preset"):
        backend._last_brush_preset = {}
    backend._last_brush_preset.update(data)
    if "engine_type" in data:
        backend.set_engine_type(int(data["engine_type"]))
    if "brush_size" in data:
        backend.set_brush_size(float(data["brush_size"]))
    if "opacity" in data:
        backend.set_brush_opacity(float(data["opacity"]))
    if "spacing_factor" in data:
        backend.set_brush_spacing(float(data["spacing_factor"]))
    if "hardness" in data:
        backend.set_brush_hardness(float(data["hardness"]))
    if "brush_grain_enabled" in data:
        backend.set_brush_grain_enabled(bool(data["brush_grain_enabled"]))
    if "brush_height_preset" in data:
        backend.set_brush_height_preset(int(data["brush_height_preset"]))
    if "brush_grain_contrast" in data:
        backend.set_brush_grain_contrast(float(data["brush_grain_contrast"]))
    if "brush_grain_scale" in data:
        backend.set_brush_grain_scale(float(data["brush_grain_scale"]))
    if "brush_grain_invert" in data:
        backend.set_brush_invert_height(bool(data["brush_grain_invert"]))
    if "shape_preset" in data:
        backend.set_shape_preset(int(data["shape_preset"]))
    if "stabilizer_weight" in data:
        backend.set_stabilizer_weight(float(data["stabilizer_weight"]))
    elif "stabilizer" in data:
        backend.set_stabilizer_weight(float(data["stabilizer"]))

    key_mappings = {
        "min_size_percent": ("root", "min_size_percent"),
        "min_opacity_percent": ("root", "min_opacity_percent"),
        "pressure_size_enabled": ("root", "pressure_size_enabled"),
        "pressure_flow_enabled": ("root", "pressure_flow_enabled"),
        "tip_aspect": ("tip", "aspect_ratio"),
        "tip_angle": ("tip", "angle"),
        "follow_stroke": ("tip", "follow_stroke"),
        "stroke_taper_enabled": ("root", "stroke_taper_enabled"),
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
            backend.set_brush_param(grp, prop, data[k])
