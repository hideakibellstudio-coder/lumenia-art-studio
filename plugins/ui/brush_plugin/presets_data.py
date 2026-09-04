"""
brush_presets.py — Categorias de Mini-Motores e Receitas Curadas
Pilar UI (PySide6) — Dados puros sem lógica de motor.

Estrutura:
  BRUSH_CATEGORIES: lista de categorias, cada uma com:
    - id: identificador interno
    - label: texto do combobox de categoria
    - engine_type: índice do EngineType C++ (0=Brush, 1=Pencil, 2=Inker, 3=Eraser...)
    - icon: emoji para o combobox
    - available: True = implementado, False = planejado (Fase futura)
    - visible_groups: grupos de parâmetros que aparecem para esta categoria
    - blend_mode_enabled: se o combobox de blend mode fica ativo
    - presets: lista de receitas curadas para o motor
"""

# Grupos de parâmetros que podem aparecer/sumir dinamicamente por categoria
# Mapeados por chave de string → usado em control_panel.py para setVisible()
PARAM_GROUPS = {
    "size_opacity",     # Tamanho, Opacidade, Blend Mode — SEMPRE visível
    "geometry",         # Ângulo, Elipse, Follow Stroke
    "jitters",          # Jitter Tamanho, Rotação, Posição
    "scatter",          # Borrifo / Spray (scatterCount)
    "textures",         # Texturas do Pincel + Papel (Brush + Canvas Heightmap)
    "velocity",         # Ativar Variação por Velocidade
    "pencil_params",    # Dureza do Grafite + Tilt Shading (exclusivo Pencil)
    "inker_params",     # Taxa de Vazão + Taper Smoothing (exclusivo Inker)
    "marker_params",    # Umidade do Solvente + Borda (exclusivo Marker) [Fase 2]
    "blur_params",      # Raio + Força do Blur (exclusivo Blur) [Fase 2]
    "smudge_params",    # Coleta de Cor + Mix + Arrasto (exclusivo Smudge) [Fase 3]
}

BRUSH_CATEGORIES = [
    # ─────────────────────────────────────────────────────────────────────────
    # Categoria 0: Pincel Básico (motor genérico existente)
    # ─────────────────────────────────────────────────────────────────────────
    {
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
            },
            {
                "label": "Pincel Suave",
                "brush_size": 30.0, "min_size_percent": 0.1,
                "opacity": 0.85, "min_opacity_percent": 0.0,
                "hardness": 0.2, "spacing_factor": 0.08,
                "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
                "brush_grain_enabled": False,
            },
            {
                "label": "Pincel Chato (Flat)",
                "brush_size": 24.0, "min_size_percent": 0.05,
                "opacity": 1.0, "min_opacity_percent": 0.0,
                "hardness": 0.9, "spacing_factor": 0.06,
                "tip_angle": 0.0, "tip_aspect": 0.3, "follow_stroke": True,
                "brush_grain_enabled": False,
            },
            {
                "label": "Aerógrafo",
                "brush_size": 40.0, "min_size_percent": 0.2,
                "opacity": 0.4, "min_opacity_percent": 0.0,
                "hardness": 0.0, "spacing_factor": 0.05,
                "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
                "brush_grain_enabled": False,
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # Categoria 1: Lápis & Carvão (PencilEngine)
    # ─────────────────────────────────────────────────────────────────────────
    {
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
    },

    # ─────────────────────────────────────────────────────────────────────────
    # Categoria 2: Caneta & Nanquim (InkerEngine)
    # ─────────────────────────────────────────────────────────────────────────
    {
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
            },
            {
                "label": "Pena Redonda",
                "brush_size": 4.0, "min_size_percent": 0.0,
                "opacity": 1.0, "min_opacity_percent": 0.0,
                "hardness": 1.0, "spacing_factor": 0.035,
                "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
                "inker_flow_rate": 1.0, "inker_taper_smoothing": 0.5,
            },
            {
                "label": "Nanquim Técnico",
                "brush_size": 3.0, "min_size_percent": 0.8,
                "opacity": 1.0, "min_opacity_percent": 0.0,
                "hardness": 1.0, "spacing_factor": 0.035,
                "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
                "inker_flow_rate": 1.0, "inker_taper_smoothing": 0.0,
            },
            {
                "label": "Caneta Tinteiro",
                "brush_size": 5.0, "min_size_percent": 0.0,
                "opacity": 0.95, "min_opacity_percent": 0.0,
                "hardness": 0.95, "spacing_factor": 0.035,
                "tip_angle": 45.0, "tip_aspect": 0.6, "follow_stroke": True,
                "inker_flow_rate": 0.9, "inker_taper_smoothing": 0.4,
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # Categoria 3: Borracha (EraserEngine)
    # ─────────────────────────────────────────────────────────────────────────
    {
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
            },
            {
                "label": "Borracha Mole",
                "brush_size": 24.0, "min_size_percent": 0.2,
                "opacity": 0.8, "min_opacity_percent": 0.0,
                "hardness": 0.2, "spacing_factor": 0.04,
                "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            },
            {
                "label": "Borracha de Aerógrafo",
                "brush_size": 40.0, "min_size_percent": 0.0,
                "opacity": 0.3, "min_opacity_percent": 0.0,
                "hardness": 0.0, "spacing_factor": 0.025,
                "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # Categoria 4: Marcador & Feltro (MarkerEngine)
    # ─────────────────────────────────────────────────────────────────────────
    {
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
    },

    # ─────────────────────────────────────────────────────────────────────────
    # Categoria 5: Blur / Desfoque (BlurEngine)
    # ─────────────────────────────────────────────────────────────────────────
    {
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
    },

    # ─────────────────────────────────────────────────────────────────────────
    # Categoria 6: Smudge / Arrasto (SmudgeEngine)
    # ─────────────────────────────────────────────────────────────────────────
    {
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
    },
    # ─────────────────────────────────────────────────────────────────────────
    # Categoria 7: Aquarela Realista (WatercolorEngine)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id": "watercolor",
        "label": "Aquarela Realista",
        "icon_key": "watercolor",
        "engine_type": 7,  # EngineType.Watercolor
        "available": True,
        "blend_mode_enabled": False,
        "visible_groups": {"size_opacity", "geometry", "textures", "watercolor_params"},
        "presets": [
            {
                "label": "Aquarela Diluída (Wet-on-Wet)",
                "brush_size": 32.0, "min_size_percent": 0.3,
                "opacity": 0.65, "min_opacity_percent": 0.0,
                "hardness": 0.3, "spacing_factor": 0.08,
                "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
                "watercolor_water_level": 0.8, "watercolor_pigment_bleed": 0.8,
                "watercolor_fringe_intensity": 0.3, "watercolor_granulation": 0.4,
                "brush_grain_enabled": True,
                "brush_height_preset": 1,
                "brush_grain_contrast": 1.0,
                "brush_grain_scale": 1.0,
            },
            {
                "label": "Aquarela Concentrada (Wet-on-Dry)",
                "brush_size": 22.0, "min_size_percent": 0.1,
                "opacity": 0.85, "min_opacity_percent": 0.0,
                "hardness": 0.7, "spacing_factor": 0.06,
                "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
                "watercolor_water_level": 0.3, "watercolor_pigment_bleed": 0.2,
                "watercolor_fringe_intensity": 0.7, "watercolor_granulation": 0.3,
                "brush_grain_enabled": True,
                "brush_height_preset": 1,
                "brush_grain_contrast": 1.1,
                "brush_grain_scale": 1.0,
            },
            {
                "label": "Pincel Seco (Dry Brush)",
                "brush_size": 18.0, "min_size_percent": 0.0,
                "opacity": 0.9, "min_opacity_percent": 0.0,
                "hardness": 0.8, "spacing_factor": 0.1,
                "tip_angle": 30.0, "tip_aspect": 0.5, "follow_stroke": True,
                "watercolor_water_level": 0.1, "watercolor_pigment_bleed": 0.0,
                "watercolor_fringe_intensity": 0.8, "watercolor_granulation": 0.7,
                "brush_grain_enabled": True,
                "brush_height_preset": 3,
                "brush_grain_contrast": 1.6,
                "brush_grain_scale": 1.3,
            },
            {
                "label": "Veladura Transparente (Glaze)",
                "brush_size": 40.0, "min_size_percent": 0.2,
                "opacity": 0.4, "min_opacity_percent": 0.0,
                "hardness": 0.2, "spacing_factor": 0.08,
                "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
                "watercolor_water_level": 0.5, "watercolor_pigment_bleed": 0.3,
                "watercolor_fringe_intensity": 0.5, "watercolor_granulation": 0.2,
                "brush_grain_enabled": True,
                "brush_height_preset": 1,
                "brush_grain_contrast": 1.0,
                "brush_grain_scale": 1.0,
            },
        ],
    },
    # ─────────────────────────────────────────────────────────────────────────
    # Categoria 8: Óleo 3D & Impasto (OilImpastoEngine)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id": "oil",
        "label": "Óleo 3D & Impasto",
        "icon_key": "oil_impasto",
        "engine_type": 8,  # EngineType.OilImpasto
        "available": True,
        "blend_mode_enabled": False,
        "visible_groups": {"size_opacity", "geometry", "textures", "oil_params"},
        "presets": [
            {
                "label": "Espátula de Impasto (Palette Knife)",
                "brush_size": 28.0, "min_size_percent": 0.4,
                "opacity": 0.95, "min_opacity_percent": 0.0,
                "hardness": 0.9, "spacing_factor": 0.05,
                "tip_angle": 45.0, "tip_aspect": 0.3, "follow_stroke": True,
                "oil_impasto_depth": 0.9, "oil_bristle_grooves": 0.0,
                "oil_viscosity": 0.8, "oil_specular_brilliance": 0.7,
                "brush_grain_enabled": True,
                "brush_height_preset": 2,
                "brush_grain_contrast": 1.1,
                "brush_grain_scale": 1.0,
            },
            {
                "label": "Pincel de Cerda Pesada (Heavy Bristle)",
                "brush_size": 24.0, "min_size_percent": 0.2,
                "opacity": 0.85, "min_opacity_percent": 0.0,
                "hardness": 0.7, "spacing_factor": 0.06,
                "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
                "oil_impasto_depth": 0.7, "oil_bristle_grooves": 0.8,
                "oil_viscosity": 0.6, "oil_specular_brilliance": 0.5,
                "brush_grain_enabled": True,
                "brush_height_preset": 2,
                "brush_grain_contrast": 1.2,
                "brush_grain_scale": 1.0,
            },
            {
                "label": "Óleo Glaze Viscoso (Viscous Glaze)",
                "brush_size": 36.0, "min_size_percent": 0.3,
                "opacity": 0.6, "min_opacity_percent": 0.0,
                "hardness": 0.4, "spacing_factor": 0.08,
                "tip_angle": 0.0, "tip_aspect": 1.0, "follow_stroke": False,
                "oil_impasto_depth": 0.3, "oil_bristle_grooves": 0.3,
                "oil_viscosity": 0.4, "oil_specular_brilliance": 0.8,
                "brush_grain_enabled": True,
                "brush_height_preset": 2,
                "brush_grain_contrast": 1.0,
                "brush_grain_scale": 1.0,
            },
            {
                "label": "Pincel de Carga Seca (Dry Scumble)",
                "brush_size": 20.0, "min_size_percent": 0.1,
                "opacity": 0.75, "min_opacity_percent": 0.0,
                "hardness": 0.85, "spacing_factor": 0.12,
                "tip_angle": 15.0, "tip_aspect": 0.6, "follow_stroke": True,
                "oil_impasto_depth": 0.5, "oil_bristle_grooves": 0.6,
                "oil_viscosity": 0.9, "oil_specular_brilliance": 0.2,
                "brush_grain_enabled": True,
                "brush_height_preset": 2,
                "brush_grain_contrast": 1.5,
                "brush_grain_scale": 1.2,
            },
        ],
    },
]

# ─────────────────────────────────────────────────────────────────────────
# Calibração Padrão de Estabilização por Categoria e Preset (Single Source of Truth)
# ─────────────────────────────────────────────────────────────────────────
CATEGORY_DEFAULT_STABILIZER = {
    "brush": 0.40,        # Pintura & Ilustração (40%)
    "pencil": 0.20,       # Fluido (20%)
    "inker": 0.65,        # Lineart & Mangá (65%)
    "eraser": 0.30,       # Borracha (30%)
    "marker": 0.45,       # Marcador (45%)
    "blur": 0.20,         # Desfoque (20%)
    "smudge": 0.25,       # Arrasto (25%)
    "watercolor": 0.35,   # Aquarela (35%)
    "oil": 0.40,          # Óleo (40%)
}

PRESET_SPECIFIC_STABILIZER = {
    "G-Pen (Mangá)": 0.65,
    "Pena Redonda": 0.60,
    "Nanquim Técnico": 0.70,
    "Caneta Tinteiro": 0.55,
    "Lápis 2H (Duro)": 0.20,
    "Lápis HB (Médio)": 0.20,
    "Lápis 6B (Mole)": 0.25,
    "Carvão Vegetal": 0.15,
    "Giz de Pastel": 0.15,
    "Pincel Chato (Flat)": 0.45,
    "Aerógrafo": 0.25,
    "Borracha Dura": 0.30,
    "Borracha Mole": 0.20,
    "Borracha de Aerógrafo": 0.15,
}

for _cat in BRUSH_CATEGORIES:
    _cat_default_stab = CATEGORY_DEFAULT_STABILIZER.get(_cat.get("id"), 0.40)
    for _p in _cat.get("presets", []):
        if "stabilizer_weight" not in _p:
            _lbl = _p.get("label", "")
            _p["stabilizer_weight"] = PRESET_SPECIFIC_STABILIZER.get(_lbl, _cat_default_stab)

# Mapa rápido id → categoria para lookup por engine_type
ENGINE_TYPE_TO_CATEGORY = {cat["engine_type"]: cat for cat in BRUSH_CATEGORIES}

PRESET_I18N_KEYS = {
    "Pincel Redondo": "brush_preset.round",
    "Pincel Suave": "brush_preset.soft",
    "Pincel Chato (Flat)": "brush_preset.flat",
    "Aerógrafo": "brush_preset.airbrush",
    "Lápis 2H (Duro)": "brush_preset.pencil_2h",
    "Lápis HB (Médio)": "brush_preset.pencil_hb",
    "Lápis 6B (Mole)": "brush_preset.pencil_6b",
    "Carvão Vegetal": "brush_preset.charcoal",
    "Giz de Pastel": "brush_preset.pastel",
    "G-Pen (Mangá)": "brush_preset.gpen",
    "Pena Redonda": "brush_preset.round_pen",
    "Nanquim Técnico": "brush_preset.technical_pen",
    "Caneta Tinteiro": "brush_preset.fountain_pen",
    "Borracha Dura": "brush_preset.hard_eraser",
    "Borracha Mole": "brush_preset.soft_eraser",
    "Borracha de Aerógrafo": "brush_preset.airbrush_eraser",
    "Marcador Copic": "brush_preset.copic_marker",
    "Caneta Feltro": "brush_preset.felt_pen",
    "Marcador Permanente": "brush_preset.permanent_marker",
    "Desfoque Suave": "brush_preset.soft_blur",
    "Desfoque Intenso": "brush_preset.strong_blur",
    "Desfoque de Borda (Foco)": "brush_preset.edge_blur",
    "Esfuminho Suave": "brush_preset.soft_smudge",
    "Arrasto de Óleo": "brush_preset.oil_smudge",
    "Misturador de Cor (Pena)": "brush_preset.color_mixer",
    "Aquarela Diluída (Wet-on-Wet)": "brush_preset.watercolor_diluted",
    "Aquarela Concentrada (Wet-on-Dry)": "brush_preset.watercolor_concentrated",
    "Pincel Seco (Dry Brush)": "brush_preset.dry_brush",
    "Veladura Transparente (Glaze)": "brush_preset.glaze",
    "Espátula de Impasto (Palette Knife)": "brush_preset.impasto_knife",
    "Pincel de Cerda Pesada (Heavy Bristle)": "brush_preset.heavy_bristle",
    "Óleo Glaze Viscoso (Viscous Glaze)": "brush_preset.viscous_glaze",
    "Pincel de Carga Seca (Dry Scumble)": "brush_preset.dry_scumble",
}

CATEGORY_I18N_KEYS = {
    "brush": "brush.preset_category_brush",
    "pencil": "brush.preset_category_pencil",
    "inker": "brush.preset_category_ink",
    "eraser": "brush.preset_category_eraser",
    "marker": "brush.preset_category_marker",
    "blur": "brush.preset_category_blur",
    "smudge": "brush.preset_category_smudge",
    "watercolor": "brush.preset_category_watercolor",
    "oil": "brush.preset_category_paint",
}


def get_preset_display_name(raw_name: str) -> str:
    from ui.core.i18n import tr
    if raw_name in PRESET_I18N_KEYS:
        return tr(PRESET_I18N_KEYS[raw_name], raw_name)
    return raw_name


def get_category_display_name(cat_id: str, default_label: str = "") -> str:
    from ui.core.i18n import tr
    if cat_id in CATEGORY_I18N_KEYS:
        return tr(CATEGORY_I18N_KEYS[cat_id], default_label or cat_id)
    return default_label or cat_id
