"""Pencil and Inker categories and presets.

Decoupled under ARCcC v2.
"""

PENCIL_CATEGORY = {
    "id": "pencil",
    "label": "Lápis & Carvão",
    "icon_key": "pencil",
    "engine_type": 1,  # EngineType.Pencil
    "available": True,
    "blend_mode_enabled": True,
    "visible_groups": {"size_opacity", "geometry", "jitters", "textures", "velocity", "pencil_params"},
    "presets": [
        {
            "label": "Lápis 2H (Duro)",
            "brush_size": 4.0, "min_size_percent": 0.0,
            "opacity": 0.65, "min_opacity_percent": 0.0,
            "hardness": 0.9, "spacing_factor": 0.08,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "pencil_graphite_hardness": 0.9,  # 2H
            "pencil_tilt_shading": False,
            "brush_grain_enabled": True,
            "brush_height_preset": 0,
            "brush_grain_contrast": 1.2,
            "brush_grain_scale": 1.0,
        },
        {
            "label": "Lápis HB (Médio)",
            "brush_size": 6.0, "min_size_percent": 0.0,
            "opacity": 0.75, "min_opacity_percent": 0.0,
            "hardness": 0.8, "spacing_factor": 0.07,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "pencil_graphite_hardness": 0.5,  # HB
            "pencil_tilt_shading": False,
            "brush_grain_enabled": True,
            "brush_height_preset": 0,
            "brush_grain_contrast": 1.1,
            "brush_grain_scale": 1.0,
        },
        {
            "label": "Lápis 6B (Mole)",
            "brush_size": 8.0, "min_size_percent": 0.0,
            "opacity": 0.90, "min_opacity_percent": 0.0,
            "hardness": 0.6, "spacing_factor": 0.06,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "pencil_graphite_hardness": 0.1,  # 6B ultra mole
            "pencil_tilt_shading": False,
            "brush_grain_enabled": True,
            "brush_height_preset": 0,
            "brush_grain_contrast": 1.0,
            "brush_grain_scale": 1.0,
        },
        {
            "label": "Carvão Vegetal",
            "brush_size": 16.0, "min_size_percent": 0.0,
            "opacity": 0.80, "min_opacity_percent": 0.0,
            "hardness": 0.4, "spacing_factor": 0.09,
            "tip_angle": 0.0, "tip_aspect": 0.7, "follow_stroke": True,
            "pencil_graphite_hardness": 0.15,
            "pencil_tilt_shading": True,
            "brush_grain_enabled": True,
            "brush_height_preset": 3,
            "brush_grain_contrast": 1.5,
            "brush_grain_scale": 1.2,
        },
        {
            "label": "Giz de Pastel",
            "brush_size": 20.0, "min_size_percent": 0.0,
            "opacity": 0.70, "min_opacity_percent": 0.0,
            "hardness": 0.3, "spacing_factor": 0.09,
            "tip_angle": 0.0, "tip_aspect": 0.6, "follow_stroke": True,
            "pencil_graphite_hardness": 0.2,
            "pencil_tilt_shading": True,
            "brush_grain_enabled": True,
            "brush_height_preset": 1,
            "brush_grain_contrast": 1.4,
            "brush_grain_scale": 1.1,
        },
    ],
}

INKER_CATEGORY = {
    "id": "inker",
    "label": "Caneta & Nanquim",
    "icon_key": "pen_tool",
    "engine_type": 2,  # EngineType.Inker
    "available": True,
    "blend_mode_enabled": True,
    "visible_groups": {"size_opacity", "geometry", "inker_params"},
    "presets": [
        {
            "label": "G-Pen (Mangá)",
            "brush_size": 6.0, "min_size_percent": 0.0,
            "opacity": 1.0, "min_opacity_percent": 0.0,
            "hardness": 1.0, "spacing_factor": 0.035,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "inker_flow_rate": 1.0, "inker_taper_smoothing": 0.7,
            "stabilizer_weight": 0.55, "stroke_taper_enabled": True,
        },
        {
            "label": "Pena Redonda",
            "brush_size": 4.0, "min_size_percent": 0.0,
            "opacity": 1.0, "min_opacity_percent": 0.0,
            "hardness": 1.0, "spacing_factor": 0.035,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "inker_flow_rate": 1.0, "inker_taper_smoothing": 0.5,
            "stabilizer_weight": 0.50, "stroke_taper_enabled": True,
        },
        {
            "label": "Nanquim Técnico",
            "brush_size": 3.0, "min_size_percent": 0.8,
            "opacity": 1.0, "min_opacity_percent": 0.0,
            "hardness": 1.0, "spacing_factor": 0.035,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "inker_flow_rate": 1.0, "inker_taper_smoothing": 0.0,
            "stabilizer_weight": 0.65, "stroke_taper_enabled": True,
        },
        {
            "label": "Caneta Tinteiro",
            "brush_size": 5.0, "min_size_percent": 0.0,
            "opacity": 0.95, "min_opacity_percent": 0.0,
            "hardness": 0.95, "spacing_factor": 0.035,
            "tip_angle": 45.0, "tip_aspect": 0.6, "follow_stroke": True,
            "inker_flow_rate": 0.9, "inker_taper_smoothing": 0.4,
            "stabilizer_weight": 0.45, "stroke_taper_enabled": True,
        },
    ],
}
