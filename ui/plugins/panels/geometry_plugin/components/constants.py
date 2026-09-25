"""Constants and Identifier mappings for Rulers and Symmetry."""

from __future__ import annotations

from ui.core.geometry.guide_type import GUIDE_TYPE_ORDER

# Fonte unica: ui.core.geometry.guide_type.GuideType (espelha o enum nativo
# GuideType 1:1 -- ver esse modulo para o porque desta lista nao ser mais
# escrita a mao aqui).
GUIDE_TYPES = [t.key for t in GUIDE_TYPE_ORDER]

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

# SymmetryMode nao tem uma chave de string por membro (mirror_v/mirror_h
# colapsam para o mesmo SymmetryMode.MIRROR nativo -- ver
# ui.core.geometry.symmetry_mode para o porque), entao esta lista continua
# escrita a mao; SYM_NAMES/SYM_KEYS abaixo tem que casar item a item com ela.
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
    from ui.infrastructure.i18n import tr
    if 0 <= idx < len(GUIDE_KEYS):
        default = GUIDE_NAMES[idx] if idx < len(GUIDE_NAMES) else ""
        return tr(GUIDE_KEYS[idx], default)
    return ""


def get_sym_name(idx: int) -> str:
    from ui.infrastructure.i18n import tr
    if 0 <= idx < len(SYM_KEYS):
        default = SYM_NAMES[idx] if idx < len(SYM_NAMES) else ""
        return tr(SYM_KEYS[idx], default)
    return ""
