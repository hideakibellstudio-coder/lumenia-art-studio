"""Ícones da interface: catálogo SVG em código e fábrica de QIcon colorido.

Porta de entrada: `get_icon(nome, cor)`. O catálogo (`SVG_ICONS`, `ALIASES`)
é exportado para quem precisa renderizar fora do QIcon (QSS do tema).
"""
from .icon_factory import clear_icon_cache, get_icon, set_color_resolver, svg_to_icon
from .svg_catalog import ALIASES, SVG_ICONS

__all__ = ["ALIASES", "SVG_ICONS", "clear_icon_cache", "get_icon", "set_color_resolver", "svg_to_icon"]
