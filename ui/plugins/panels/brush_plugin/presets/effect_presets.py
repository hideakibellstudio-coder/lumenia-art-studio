"""Marker, Blur, and Smudge categories and presets.

Decoupled under ARCcC v2.
"""

MARKER_CATEGORY = {
    "id": "marker",
    "label": "Marcador & Feltro",
    "icon_key": "marker",
    "engine_type": 4,  # EngineType.Marker
    "available": True,
    "blend_mode_enabled": False,
    "visible_groups": {"size_opacity", "geometry", "marker_params"},
    "presets": [
        {
            "label": "Marcador Copic",
            "brush_size": 24.0, "min_size_percent": 0.2,
            "opacity": 0.7, "min_opacity_percent": 0.0,
            "hardness": 0.80, "spacing_factor": 0.04,
            "tip_angle": 45.0, "tip_aspect": 0.4, "follow_stroke": True,
            "marker_solvent_wetness": 0.6, "marker_edge_darkening": 0.3,
        },
        {
            "label": "Caneta Feltro",
            "brush_size": 12.0, "min_size_percent": 0.5,
            "opacity": 0.85, "min_opacity_percent": 0.0,
            "hardness": 0.85, "spacing_factor": 0.04,
            "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            "marker_solvent_wetness": 0.3, "marker_edge_darkening": 0.2,
        },
        {
            "label": "Marcador Permanente",
            "brush_size": 18.0, "min_size_percent": 0.8,
            "opacity": 0.95, "min_opacity_percent": 0.0,
            "hardness": 0.90, "spacing_factor": 0.04,
            "tip_angle": 0.0, "tip_aspect": 0.5, "follow_stroke": True,
            "marker_solvent_wetness": 0.1, "marker_edge_darkening": 0.3,
        },
    ],
}

BLUR_CATEGORY = {
    "id": "blur",
    "label": "Blur / Desfoque",
    "icon_key": "blur",
    "engine_type": 5,  # EngineType.Blur
    "available": True,
    "blend_mode_enabled": False,
    "visible_groups": {"size_opacity", "blur_params"},
    "presets": [
        {
            "label": "Desfoque Suave",
            "brush_size": 36.0, "min_size_percent": 0.2,
            "opacity": 0.8, "min_opacity_percent": 0.0,
            "hardness": 0.2, "spacing_factor": 0.04,
            "blur_radius": 2, "blur_strength": 0.7,
        },
        {
            "label": "Desfoque Intenso",
            "brush_size": 50.0, "min_size_percent": 0.1,
            "opacity": 1.0, "min_opacity_percent": 0.0,
            "hardness": 0.1, "spacing_factor": 0.03,
            "blur_radius": 4, "blur_strength": 0.95,
        },
        {
            "label": "Desfoque de Borda (Foco)",
            "brush_size": 24.0, "min_size_percent": 0.5,
            "opacity": 0.7, "min_opacity_percent": 0.0,
            "hardness": 0.5, "spacing_factor": 0.04,
            "blur_radius": 2, "blur_strength": 0.5,
        },
    ],
}

SMUDGE_CATEGORY = {
    "id": "smudge",
    "label": "Smudge / Arrasto",
    "icon_key": "smudge",
    "engine_type": 6,  # EngineType.Smudge
    "available": True,
    "blend_mode_enabled": False,
    "visible_groups": {"size_opacity", "geometry", "smudge_params"},
    "presets": [
        {
            "label": "Esfuminho Suave",
            "brush_size": 28.0, "min_size_percent": 0.1,
            "opacity": 0.7, "min_opacity_percent": 0.0,
            "hardness": 0.3, "spacing_factor": 0.08,
            "smudge_color_pickup": 0.7, "smudge_mix_ratio": 0.5, "smudge_stretch": 0.8,
        },
        {
            "label": "Arrasto de Óleo",
            "brush_size": 20.0, "min_size_percent": 0.2,
            "opacity": 0.9, "min_opacity_percent": 0.0,
            "hardness": 0.7, "spacing_factor": 0.06,
            "smudge_color_pickup": 0.85, "smudge_mix_ratio": 0.7, "smudge_stretch": 0.9,
        },
        {
            "label": "Misturador de Cor (Pena)",
            "brush_size": 14.0, "min_size_percent": 0.0,
            "opacity": 0.8, "min_opacity_percent": 0.0,
            "hardness": 0.85, "spacing_factor": 0.05,
            "smudge_color_pickup": 0.5, "smudge_mix_ratio": 0.4, "smudge_stretch": 0.5,
        },
    ],
}
