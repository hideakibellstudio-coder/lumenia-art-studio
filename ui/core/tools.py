"""
ui.core.tools — Metadados de Ferramentas da Casca
==================================================
Catálogo central de ferramentas (TOOL_META) compartilhado pela barra flutuante,
pela sidebar de ferramentas, pelo painel de pincel e demais consumidores.

É parte do KERNEL da casca (ui.core): plugins podem importar daqui, mas a
casca nunca importa de plugins.
"""

from __future__ import annotations
from typing import Dict

TOOL_META: Dict[str, Dict[str, str]] = {
    "brush": {"name": "Pincel", "icon": "brush", "implemented": True},
    "eraser": {"name": "Borracha", "icon": "eraser", "implemented": True},
    "smudge": {"name": "Smudge", "icon": "smudge", "implemented": True},
    "bucket": {"name": "Balde de Tinta", "icon": "bucket", "implemented": True},
    "eyedrop": {"name": "Conta-Gotas", "icon": "eyedrop", "implemented": True},
    "wand": {"name": "Varinha Mágica", "icon": "wand", "implemented": True},
    "transform": {"name": "Transformar", "icon": "transform", "implemented": True},
    "rect_select": {"name": "Seleção Retangular", "icon": "select_rect", "implemented": True},
    "ellipse_select": {"name": "Seleção Elíptica", "icon": "select_ellipse", "implemented": True},
    "lasso": {"name": "Laço de Seleção", "icon": "lasso", "implemented": True},
    "shapes": {"name": "Formas Vetoriais", "icon": "shapes", "implemented": True},
    "shape_rect": {"name": "Retângulo", "icon": "shape_rect", "implemented": True},
    "shape_ellipse": {"name": "Elipse / Círculo", "icon": "shape_ellipse", "implemented": True},
    "shape_line": {"name": "Linha Reta", "icon": "shape_line", "implemented": True},
    "shape_polygon": {"name": "Polígono Regular", "icon": "shape_polygon", "implemented": True},
    "shape_star": {"name": "Estrela Paramétrica", "icon": "shape_star", "implemented": True},
    "text": {"name": "Texto Tipográfico", "icon": "text", "implemented": True},
}

TOOL_I18N_KEYS: Dict[str, str] = {
    "brush": "tools.brush",
    "eraser": "tools.eraser",
    "smudge": "brush.preset_category_smudge",
    "bucket": "tools.fill",
    "eyedrop": "tools.eyedropper",
    "wand": "tools.wand",
    "transform": "tools.transform",
    "rect_select": "tools.rect_select",
    "ellipse_select": "tools.ellipse_select",
    "lasso": "tools.lasso",
    "shapes": "tools.shapes",
    "shape_rect": "shapes.rectangle",
    "shape_ellipse": "shapes.ellipse",
    "shape_line": "shapes.line",
    "shape_polygon": "shapes.polygon",
    "shape_star": "shapes.star",
    "text": "tools.text",
}

DEFAULT_TOOLS = [
    "brush",
    "eraser",
    "smudge",
    "bucket",
    "eyedrop",
    "wand",
    "transform",
    "rect_select",
    "ellipse_select",
    "lasso",
    "shapes",
    "text",
]


def get_tool_name(tool_id: str) -> str:
    from ui.core.i18n import tr
    if tool_id in TOOL_I18N_KEYS:
        default_name = TOOL_META.get(tool_id, {}).get("name", tool_id)
        return tr(TOOL_I18N_KEYS[tool_id], default_name)
    return TOOL_META.get(tool_id, {}).get("name", tool_id)


__all__ = ["TOOL_META", "TOOL_I18N_KEYS", "DEFAULT_TOOLS", "get_tool_name"]