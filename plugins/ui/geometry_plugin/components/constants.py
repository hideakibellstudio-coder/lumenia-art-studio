"""Constants and Identifier mappings for Rulers and Symmetry."""

from __future__ import annotations

GUIDE_TYPES = [
    "none",           # 0
    "straight",       # 1
    "curve_ruler",    # 2
    "curvilinear",    # 3
    "one_point",      # 4
    "two_point",      # 5
    "three_point",    # 6
    "isometric",      # 7
]

GUIDE_NAMES = [
    "Nenhuma",
    "Régua Reta",
    "Régua Curva",
    "Perspectiva 6P",
    "Perspectiva 1P",
    "Perspectiva 2P",
    "Perspectiva 3P",
    "Grade Isométrica",
]

GUIDE_KEYS = [
    "geometry.none",
    "geometry.straight",
    "geometry.curve_ruler",
    "geometry.curvilinear",
    "geometry.one_point",
    "geometry.two_point",
    "geometry.three_point",
    "geometry.isometric",
]

SYM_TYPES = [
    "none",           # 0
    "mirror",         # 1
    "mirror_v",       # 2
    "mirror_h",       # 3
    "double_mirror",  # 4
    "radial",         # 5
    "kaleidoscope",   # 6
]

SYM_NAMES = [
    "Nenhuma",
    "Espelho Livre",
    "Espelho Vertical",
    "Espelho Horizontal",
    "Espelho Duplo",
    "Simetria Radial",
    "Caleidoscópio",
]

SYM_KEYS = [
    "geometry.none",
    "geometry.mirror",
    "geometry.mirror_v",
    "geometry.mirror_h",
    "geometry.double_mirror",
    "geometry.radial",
    "geometry.kaleidoscope",
]


def get_guide_name(idx: int) -> str:
    from ui.core.i18n import tr
    if 0 <= idx < len(GUIDE_KEYS):
        default = GUIDE_NAMES[idx] if idx < len(GUIDE_NAMES) else ""
        return tr(GUIDE_KEYS[idx], default)
    return ""


def get_sym_name(idx: int) -> str:
    from ui.core.i18n import tr
    if 0 <= idx < len(SYM_KEYS):
        default = SYM_NAMES[idx] if idx < len(SYM_NAMES) else ""
        return tr(SYM_KEYS[idx], default)
    return ""
