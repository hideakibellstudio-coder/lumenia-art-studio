"""Geometria da ferramenta Formas (`canvas/tools/shape_paths.py`).

Extraída de `ShapeToolController.calculate_path` em 2026-09-25; antes da troca,
1.440 arrastos aleatórios (5 formas, Shift/Alt, raios e lados variados) deram
o mesmo caminho nas duas versões. Aqui ficam as regras que o artista vê.
"""
from __future__ import annotations

import math

import pytest
from PySide6 import QtCore

from ui.plugins.system.workspace_core.workspace.canvas.tools.shape_paths import build_shape_path

P = QtCore.QPointF


def _points(path):
    return [(round(p.x(), 6), round(p.y(), 6)) for poly in path.toSubpathPolygons() for p in poly]


def test_shift_makes_the_rectangle_a_square_and_alt_grows_from_the_center():
    square = build_shape_path("shape_rect", P(10, 10), P(50, 30), {}, shift=True, alt=False).boundingRect()
    assert (square.width(), square.height()) == (40, 40)
    centered = build_shape_path("shape_rect", P(100, 100), P(120, 110), {}, shift=False, alt=True).boundingRect()
    assert centered.center() == P(100, 100) and (centered.width(), centered.height()) == (40, 20)


def test_ellipse_uses_the_same_box_as_the_rectangle():
    for shift in (False, True):
        for alt in (False, True):
            rect = build_shape_path("shape_rect", P(0, 0), P(30, -20), {}, shift, alt).boundingRect()
            ellipse = build_shape_path("shape_ellipse", P(0, 0), P(30, -20), {}, shift, alt).boundingRect()
            assert rect == ellipse


def test_shift_snaps_the_line_to_15_degrees():
    pts = _points(build_shape_path("shape_line", P(0, 0), P(100, 12), {}, shift=True, alt=False))
    (x0, y0), (x1, y1) = pts
    assert math.degrees(math.atan2(y1 - y0, x1 - x0)) == pytest.approx(0.0, abs=1e-6)


def test_polygon_and_star_vertices():
    polygon = _points(build_shape_path("shape_polygon", P(0, 0), P(100, 0), {"polygon_sides": 6}, False, False))
    assert len(set(polygon)) == 6
    star = build_shape_path("shape_star", P(0, 0), P(100, 0), {"star_points": 5, "star_inner_ratio": 0.5}, False, True)
    radii = sorted({round(math.hypot(x, y), 3) for x, y in _points(star)})
    assert radii == [50.0, 100.0], "vértices alternam raio externo e interno (a partir do centro com Alt)"


def test_tiny_or_unknown_shapes_have_no_path():
    assert build_shape_path("shape_polygon", P(0, 0), P(0.5, 0), {}, False, False) is None
    assert build_shape_path("shape_star", P(0, 0), P(0.5, 0), {}, False, False) is None
    assert build_shape_path("shape_blob", P(0, 0), P(50, 50), {}, False, False) is None
