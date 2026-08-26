"""
ui.core.tools — Metadados de Ferramentas da Casca
==================================================
Catálogo central de ferramentas (TOOL_META) compartilhado pela barra flutuante,
pela sidebar de ferramentas, pelo painel de pincel e demais consumidores.

É parte do KERNEL da casca (ui.core): plugins podem importar daqui, mas a
casca nunca importa de plugins.
"""

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

DEFAULT_TOOLS = ["brush", "eraser", "smudge", "bucket", "eyedrop", "text", "shapes", "wand", "transform", "rect_select", "ellipse_select", "lasso"]

__all__ = ["TOOL_META", "DEFAULT_TOOLS"]