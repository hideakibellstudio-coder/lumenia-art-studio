"""
ui.infrastructure.icons — Catálogo Centralizado de Ícones Vetoriais SVG Dinâmicos
=======================================================================
Fornece ícones vetoriais com suporte nativo a currentColor (adaptação a temas
claros e escuros via IconManager / ThemeManager) com acabamento profissional.
"""

from typing import Callable, Optional

from PySide6 import QtGui, QtCore, QtSvg
import xml.etree.ElementTree as ET

from ui.infrastructure.icons.svg_catalog import SVG_ICONS, ALIASES

_ICON_CACHE: dict = {}

# Cor de um token do tema ("text_main", "accent"...). Quem registra é o
# ThemeManager ao ser criado: os ícones não conhecem o tema. Até 2026-09-24
# este módulo importava o ThemeManager dentro de get_icon e o tema importava o
# catálogo de ícones (ciclo entre as duas pastas). Sem tema registrado, o SVG
# fica com `currentColor` (o renderizador do Qt desenha em preto).
_resolve_color: Callable[[str], Optional[str]] = lambda _token: None


def set_color_resolver(resolver: Callable[[str], Optional[str]]) -> None:
    """Chamado pelo ThemeManager: token do tema -> cor "#rrggbb"."""
    global _resolve_color
    _resolve_color = resolver

def clear_icon_cache(*args):
    """Limpa o cache de ícones quando o tema muda."""
    _ICON_CACHE.clear()


def svg_to_icon(svg_xml: str, size: QtCore.QSize = QtCore.QSize(24, 24)) -> QtGui.QIcon:
    byte_array = QtCore.QByteArray(svg_xml.encode('utf-8'))
    renderer = QtSvg.QSvgRenderer(byte_array)

    pixmap = QtGui.QPixmap(size)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QtGui.QIcon(pixmap)


def get_icon(name: str, color: str = None, size: QtCore.QSize = QtCore.QSize(24, 24)) -> QtGui.QIcon:
    """Retorna um QIcon estável, rápido e thread-safe renderizado a partir do SVG."""
    if not name:
        return QtGui.QIcon()

    name = str(name).replace("-", "_").replace(" ", "_")
    resolved_name = ALIASES.get(name, name)
    svg_template = SVG_ICONS.get(resolved_name)
    if not svg_template:
        return QtGui.QIcon()

    if not color or not color.startswith("#"):
        color = _resolve_color(color if color else "text_main")

    cache_key = (resolved_name, color, size.width(), size.height())
    if cache_key in _ICON_CACHE:
        return QtGui.QIcon(_ICON_CACHE[cache_key])

    svg_xml = svg_template.replace("currentColor", color) if color else svg_template
    icon = svg_to_icon(svg_xml, size)
    _ICON_CACHE[cache_key] = icon
    return QtGui.QIcon(icon)
