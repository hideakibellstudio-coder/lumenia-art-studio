"""Geometria das formas da ferramenta Formas: o caminho (QPainterPath) de cada
forma a partir do arraste, com Shift (proporção/ângulo em passos de 15°) e Alt
(a partir do centro).

Funções puras, sem estado. Extraídas de `ShapeToolController.calculate_path`
em 2026-09-25 (complexidade 22); retângulo e elipse repetiam o cálculo da
caixa, que agora é um só (`_box`).
"""

from __future__ import annotations

import math
from typing import Callable, Optional

from PySide6 import QtCore, QtGui

_SNAP = math.radians(15.0)


def _snap_angle(angle: float) -> float:
    return round(angle / _SNAP) * _SNAP


def _line(p1: QtCore.QPointF, p2: QtCore.QPointF, settings: dict, shift: bool, alt: bool) -> QtGui.QPainterPath:
    dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
    length = math.hypot(dx, dy)
    if shift and length > 1e-4:
        angle = _snap_angle(math.atan2(dy, dx))
        p2 = QtCore.QPointF(p1.x() + length * math.cos(angle), p1.y() + length * math.sin(angle))
    start = QtCore.QPointF(p1.x() - (p2.x() - p1.x()), p1.y() - (p2.y() - p1.y())) if alt else p1
    path = QtGui.QPainterPath()
    path.moveTo(start)
    path.lineTo(p2)
    return path


def _box(p1: QtCore.QPointF, p2: QtCore.QPointF, shift: bool, alt: bool) -> QtCore.QRectF:
    dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
    if shift:
        side = max(abs(dx), abs(dy))
        dx = side if dx >= 0 else -side
        dy = side if dy >= 0 else -side
    if alt:
        return QtCore.QRectF(p1.x() - abs(dx), p1.y() - abs(dy), abs(dx) * 2.0, abs(dy) * 2.0)
    return QtCore.QRectF(min(p1.x(), p1.x() + dx), min(p1.y(), p1.y() + dy), abs(dx), abs(dy))


def _rect(p1, p2, settings, shift, alt) -> QtGui.QPainterPath:
    rect = _box(p1, p2, shift, alt)
    radius = float(settings.get("corner_radius", 0))
    path = QtGui.QPainterPath()
    if radius > 0:
        r = min(radius, min(rect.width(), rect.height()) / 2.0)
        path.addRoundedRect(rect, r, r)
    else:
        path.addRect(rect)
    return path


def _ellipse(p1, p2, settings, shift, alt) -> QtGui.QPainterPath:
    path = QtGui.QPainterPath()
    path.addEllipse(_box(p1, p2, shift, alt))
    return path


def _radial(p1, p2, shift, alt, radii: list[float], step: float) -> Optional[QtGui.QPainterPath]:
    """Polígono de vértices em volta de um centro; `radii` se repete por vértice."""
    dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
    start = math.atan2(dy, dx)
    if shift:
        start = _snap_angle(start)
    center = p1 if alt else QtCore.QPointF(p1.x() + dx / 2.0, p1.y() + dy / 2.0)
    scale = 1.0 if alt else 0.5
    poly = QtGui.QPolygonF()
    for i in range(len(radii)):
        angle = start + step * i
        r = radii[i] * scale
        poly.append(QtCore.QPointF(center.x() + r * math.cos(angle), center.y() + r * math.sin(angle)))
    path = QtGui.QPainterPath()
    path.addPolygon(poly)
    path.closeSubpath()
    return path


def _polygon(p1, p2, settings, shift, alt) -> Optional[QtGui.QPainterPath]:
    radius = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
    if radius < 1.0:
        return None
    sides = max(3, int(settings.get("polygon_sides", 5)))
    return _radial(p1, p2, shift, alt, [radius] * sides, 2.0 * math.pi / sides)


def _star(p1, p2, settings, shift, alt) -> Optional[QtGui.QPainterPath]:
    r_outer = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
    if r_outer < 1.0:
        return None
    points = max(3, int(settings.get("star_points", 5)))
    r_inner = r_outer * float(settings.get("star_inner_ratio", 0.5))
    return _radial(p1, p2, shift, alt, [r_outer, r_inner] * points, math.pi / points)


_BUILDERS: dict[str, Callable] = {
    "shape_line": _line,
    "shape_rect": _rect,
    "shape_ellipse": _ellipse,
    "shape_polygon": _polygon,
    "shape_star": _star,
}


def build_shape_path(shape_type: str, p1: QtCore.QPointF, p2: QtCore.QPointF, settings: dict,
                     shift: bool, alt: bool) -> Optional[QtGui.QPainterPath]:
    """Caminho da forma, ou None (forma desconhecida ou pequena demais)."""
    builder = _BUILDERS.get(shape_type)
    return builder(p1, p2, settings, shift, alt) if builder else None
