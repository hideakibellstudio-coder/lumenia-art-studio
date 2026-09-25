"""Transformar -> Distorcer: geometria do quadrilátero de destino.

Criado em 2026-09-23 (antes o modo "Distorcer" fazia o mesmo que "Livre").
O quadrilátero é sempre a lista de 4 cantos TL, TR, BR, BL em coordenadas da
tela. A prévia usa QTransform.quadToQuad e o commit usa a homografia do motor
(engine/core/raster/transform/Homography.hpp): a transformação projetiva que
leva 4 pontos em 4 pontos é única, então prévia e resultado coincidem.
"""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui

CORNERS = ("tl", "tr", "br", "bl")
EDGES = {"tc": ("tl", "tr"), "mr": ("tr", "br"), "bc": ("br", "bl"), "ml": ("bl", "tl")}

Quad = list[QtCore.QPointF]


def rect_corners(rect: QtCore.QRectF) -> Quad:
    return [rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft()]


def quad_from_matrix(rect: QtCore.QRectF, matrix: QtGui.QTransform) -> Quad:
    """Onde a caixa está agora (depois de mover/escalar/girar no modo livre)."""
    return [matrix.map(p) for p in rect_corners(rect)]


def matrix_from_quad(rect: QtCore.QRectF, quad: Quad) -> Optional[QtGui.QTransform]:
    matrix = QtGui.QTransform()
    if not QtGui.QTransform.quadToQuad(QtGui.QPolygonF(rect_corners(rect)), QtGui.QPolygonF(quad), matrix):
        return None
    return matrix


def is_convex_quad(quad: Quad) -> bool:
    """Mesmo critério do motor (quadConvexo): 4 curvas no mesmo sentido."""
    sign = 0
    for i in range(4):
        a, b, c = quad[i], quad[(i + 1) % 4], quad[(i + 2) % 4]
        cross = (b.x() - a.x()) * (c.y() - b.y()) - (b.y() - a.y()) * (c.x() - b.x())
        if abs(cross) < 1e-6:
            return False
        s = 1 if cross > 0 else -1
        if sign == 0:
            sign = s
        elif s != sign:
            return False
    return True


def drag(start_quad: Quad, handle: str, delta: QtCore.QPointF) -> Quad:
    """Canto: move só ele. Lado: move os dois cantos do lado. "move": tudo."""
    moved = [QtCore.QPointF(p) for p in start_quad]
    if handle == "move":
        targets = CORNERS
    elif handle in CORNERS:
        targets = (handle,)
    else:
        targets = EDGES.get(handle, ())
    for corner in targets:
        moved[CORNERS.index(corner)] += delta
    return moved


def _center(quad: Quad) -> QtCore.QPointF:
    return QtCore.QPointF(sum(p.x() for p in quad) / 4.0, sum(p.y() for p in quad) / 4.0)


def mirror(quad: Quad, horizontal: bool) -> Quad:
    """Espelha o conteúdo dentro da mesma posição (reflete cada canto no centro)."""
    c = _center(quad)
    if horizontal:
        return [QtCore.QPointF(2.0 * c.x() - p.x(), p.y()) for p in quad]
    return [QtCore.QPointF(p.x(), 2.0 * c.y() - p.y()) for p in quad]


def rotate_90(quad: Quad, clockwise: bool) -> Quad:
    """Gira o quadrilátero 90° em torno do centro (y cresce para baixo)."""
    c = _center(quad)
    out = []
    for p in quad:
        dx, dy = p.x() - c.x(), p.y() - c.y()
        out.append(QtCore.QPointF(c.x() - dy, c.y() + dx) if clockwise else QtCore.QPointF(c.x() + dy, c.y() - dx))
    return out


def flatten(quad: Quad) -> list[float]:
    """[x0, y0, ..., x3, y3] no formato de commit_transform_distort."""
    return [v for p in quad for v in (p.x(), p.y())]
