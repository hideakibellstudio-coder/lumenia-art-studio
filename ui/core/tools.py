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
    "smudge": {"name": "Smudge", "icon": "smudge", "implemented": False},
    "bucket": {"name": "Balde de Tinta", "icon": "bucket", "implemented": False},
    "eyedrop": {"name": "Conta-Gotas", "icon": "eyedrop", "implemented": True},
    "wand": {"name": "Varinha Mágica", "icon": "wand", "implemented": False},
    "transform": {"name": "Transformar", "icon": "transform", "implemented": False},
    "rect_select": {"name": "Seleção Retangular", "icon": "rect_select", "implemented": False},
    "ellipse_select": {"name": "Seleção Elíptica", "icon": "ellipse_select", "implemented": False},
    "lasso": {"name": "Laço de Seleção", "icon": "lasso", "implemented": False},
}

DEFAULT_TOOLS = list(TOOL_META.keys())

__all__ = ["TOOL_META", "DEFAULT_TOOLS"]