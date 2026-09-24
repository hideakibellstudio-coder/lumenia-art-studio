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

CANTOS = ("tl", "tr", "br", "bl")
LADOS = {"tc": ("tl", "tr"), "mr": ("tr", "br"), "bc": ("br", "bl"), "ml": ("bl", "tl")}

Quad = list[QtCore.QPointF]


def cantos_do_retangulo(rect: QtCore.QRectF) -> Quad:
    return [rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft()]


def quad_da_matriz(rect: QtCore.QRectF, matriz: QtGui.QTransform) -> Quad:
    """Onde a caixa está agora (depois de mover/escalar/girar no modo livre)."""
    return [matriz.map(p) for p in cantos_do_retangulo(rect)]


def matriz_do_quad(rect: QtCore.QRectF, quad: Quad) -> Optional[QtGui.QTransform]:
    matriz = QtGui.QTransform()
    if not QtGui.QTransform.quadToQuad(QtGui.QPolygonF(cantos_do_retangulo(rect)), QtGui.QPolygonF(quad), matriz):
        return None
    return matriz


def quad_convexo(quad: Quad) -> bool:
    """Mesmo critério do motor (quadConvexo): 4 curvas no mesmo sentido."""
    sinal = 0
    for i in range(4):
        a, b, c = quad[i], quad[(i + 1) % 4], quad[(i + 2) % 4]
        cruz = (b.x() - a.x()) * (c.y() - b.y()) - (b.y() - a.y()) * (c.x() - b.x())
        if abs(cruz) < 1e-6:
            return False
        s = 1 if cruz > 0 else -1
        if sinal == 0:
            sinal = s
        elif s != sinal:
            return False
    return True


def arrastar(quad_inicial: Quad, alca: str, delta: QtCore.QPointF) -> Quad:
    """Canto: move só ele. Lado: move os dois cantos do lado. "move": tudo."""
    novo = [QtCore.QPointF(p) for p in quad_inicial]
    if alca == "move":
        alvos = CANTOS
    elif alca in CANTOS:
        alvos = (alca,)
    else:
        alvos = LADOS.get(alca, ())
    for nome in alvos:
        novo[CANTOS.index(nome)] += delta
    return novo


def _centro(quad: Quad) -> QtCore.QPointF:
    return QtCore.QPointF(sum(p.x() for p in quad) / 4.0, sum(p.y() for p in quad) / 4.0)


def espelhar(quad: Quad, horizontal: bool) -> Quad:
    """Espelha o conteúdo dentro da mesma posição (reflete cada canto no centro)."""
    c = _centro(quad)
    if horizontal:
        return [QtCore.QPointF(2.0 * c.x() - p.x(), p.y()) for p in quad]
    return [QtCore.QPointF(p.x(), 2.0 * c.y() - p.y()) for p in quad]


def girar_90(quad: Quad, horario: bool) -> Quad:
    """Gira o quadrilátero 90° em torno do centro (y cresce para baixo)."""
    c = _centro(quad)
    out = []
    for p in quad:
        dx, dy = p.x() - c.x(), p.y() - c.y()
        out.append(QtCore.QPointF(c.x() - dy, c.y() + dx) if horario else QtCore.QPointF(c.x() + dy, c.y() - dx))
    return out


def plano(quad: Quad) -> list[float]:
    """[x0, y0, ..., x3, y3] no formato de commit_transform_distort."""
    return [v for p in quad for v in (p.x(), p.y())]
