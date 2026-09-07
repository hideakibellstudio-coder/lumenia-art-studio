"""Basic brush and eraser categories and presets.

Decoupled under ARCcC v2.
"""

BRUSH_CATEGORY = {
    "id": "brush",
    "label": "Pincel Básico",
    "icon_key": "brush",
    "engine_type": 0,  # EngineType.Brush
    "available": True,
    "blend_mode_enabled": True,
    "visible_groups": {"size_opacity", "geometry", "jitters", "scatter", "textures", "velocity"},
    "presets": [
        {
            "label": "Pincel Redondo",
            "brush_size": 20.0, "min_size_percent": 0.0,
            "opacity": 1.0, "min_opacity_percent": 0.0,
            "hardness": 0.85, "spacing_factor": 0.08,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "brush_grain_enabled": False,
            "stabilizer_weight": 0.35, "stroke_taper_enabled": True,
        },
        {
            "label": "Pincel Suave",
            "brush_size": 30.0, "min_size_percent": 0.1,
            "opacity": 0.85, "min_opacity_percent": 0.0,
            "hardness": 0.2, "spacing_factor": 0.08,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "brush_grain_enabled": False,
            "stabilizer_weight": 0.30, "stroke_taper_enabled": True,
        },
        {
            "label": "Pincel Chato (Flat)",
            "brush_size": 24.0, "min_size_percent": 0.05,
            "opacity": 1.0, "min_opacity_percent": 0.0,
            "hardness": 0.9, "spacing_factor": 0.06,
            "tip_angle": 0.0, "tip_aspect": 0.3, "follow_stroke": True,
            "brush_grain_enabled": False,
            "stabilizer_weight": 0.25, "stroke_taper_enabled": True,
        },
        {
            "label": "Aerógrafo",
            "brush_size": 40.0, "min_size_percent": 0.2,
            "opacity": 0.4, "min_opacity_percent": 0.0,
            "hardness": 0.0, "spacing_factor": 0.05,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "brush_grain_enabled": False,
            "stabilizer_weight": 0.05, "stroke_taper_enabled": True,
        },
    ],
}

ERASER_CATEGORY = {
    "id": "eraser",
    "label": "Borracha",
    "icon_key": "eraser",
    "engine_type": 3,  # EngineType.Eraser
    "available": True,
    "blend_mode_enabled": False,
    "visible_groups": {"size_opacity", "geometry"},
    "presets": [
        {
            "label": "Borracha Dura",
            "brush_size": 16.0, "min_size_percent": 0.5,
            "opacity": 1.0, "min_opacity_percent": 0.0,
            "hardness": 0.95, "spacing_factor": 0.04,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "stabilizer_weight": 0.20, "stroke_taper_enabled": False,
        },
        {
            "label": "Borracha Mole",
            "brush_size": 24.0, "min_size_percent": 0.2,
            "opacity": 0.8, "min_opacity_percent": 0.0,
            "hardness": 0.2, "spacing_factor": 0.04,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "stabilizer_weight": 0.10, "stroke_taper_enabled": False,
        },
        {
            "label": "Borracha de Aerógrafo",
            "brush_size": 40.0, "min_size_percent": 0.0,
            "opacity": 0.3, "min_opacity_percent": 0.0,
            "hardness": 0.0, "spacing_factor": 0.025,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "stabilizer_weight": 0.05, "stroke_taper_enabled": False,
        },
    ],
}
