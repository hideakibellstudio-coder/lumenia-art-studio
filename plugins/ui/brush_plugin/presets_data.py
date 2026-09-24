"""presets_data — junta as categorias de `presets/` e dá nomes traduzidos a presets e categorias.

Só dados (sem Qt de interface e sem motor).
"""

from typing import Dict, Any
from .presets import (
    ALL_CATEGORIES,
    PRESET_I18N_KEYS,
    CATEGORY_I18N_KEYS,
)

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

CATEGORY_DEFAULTS = {
    "brush": {"stabilizer_weight": 0.35, "stroke_taper_enabled": True},
    "pencil": {"stabilizer_weight": 0.15, "stroke_taper_enabled": True},
    "inker": {"stabilizer_weight": 0.50, "stroke_taper_enabled": True},
    "eraser": {"stabilizer_weight": 0.15, "stroke_taper_enabled": False},
    "marker": {"stabilizer_weight": 0.20, "stroke_taper_enabled": False},
    "blur": {"stabilizer_weight": 0.10, "stroke_taper_enabled": False},
    "smudge": {"stabilizer_weight": 0.15, "stroke_taper_enabled": False},
    "watercolor": {"stabilizer_weight": 0.20, "stroke_taper_enabled": True},
    "oil": {"stabilizer_weight": 0.25, "stroke_taper_enabled": False},
}

BRUSH_CATEGORIES = ALL_CATEGORIES

# Injeta automaticamente defaults canônicos de estabilização e dinâmica se ausentes
for _cat in BRUSH_CATEGORIES:
    _cid = _cat.get("id", "brush")
    _cdefs = CATEGORY_DEFAULTS.get(_cid, {"stabilizer_weight": 0.35, "stroke_taper_enabled": True})
    for _p in _cat.get("presets", []):
        for _k, _v in _cdefs.items():
            if _k not in _p:
                _p[_k] = _v

# Mapa rápido id → categoria para lookup por engine_type
ENGINE_TYPE_TO_CATEGORY: Dict[int, Any] = {cat["engine_type"]: cat for cat in BRUSH_CATEGORIES}


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
