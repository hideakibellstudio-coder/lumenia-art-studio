"""Laço (seleção por polígono): o Anti-Alias da barra de seleção vale.

Até 2026-09-25 `SelectionEngine::generatePolygonMask` recebia `antiAliasing` e
não usava (achado pelos avisos do compilador): ligar ou desligar o botão não
mudava nada no laço. E, sem suavização, o fim de cada trecho era inclusivo: o
laço ganhava uma coluna à direita (um quadrado de 10 px virava 11 x 10).
"""
from __future__ import annotations

import pytest

native = pytest.importorskip("aladyn_engine_native")

L = 40
SQUARE = [10, 10, 20, 10, 20, 20, 10, 20]
TRIANGLE = [5, 5, 35, 5, 5, 30]


def _mask(points: list[int], anti_aliasing: bool) -> bytes:
    facade = native.PaintEngineFacade(L, L)
    assert facade.select_polygon(points, 0, anti_aliasing, 0)
    return facade.get_selection_mask_buffer()


def _selected(mask: bytes) -> set[tuple[int, int]]:
    return {(i % L, i // L) for i, value in enumerate(mask) if value == 255}


@pytest.mark.parametrize("anti_aliasing", [False, True])
def test_square_selects_exactly_its_pixels(anti_aliasing):
    mask = _mask(SQUARE, anti_aliasing)
    assert _selected(mask) == {(x, y) for x in range(10, 20) for y in range(10, 20)}
    assert all(value in (0, 255) for value in mask), "borda reta alinhada ao pixel não tem meio-tom"


def test_diagonal_edge_is_smoothed_only_with_anti_aliasing():
    hard = _mask(TRIANGLE, False)
    smooth = _mask(TRIANGLE, True)
    assert set(hard) == {0, 255}
    partial = [value for value in smooth if 0 < value < 255]
    assert len(partial) >= 25, "a hipotenusa deveria ter uma rampa de cobertura"
    # A área selecionada é a mesma: a suavização só redistribui a borda.
    assert abs(sum(smooth) - sum(hard)) / 255 < 0.03 * (30 * 25 / 2)


def test_smoothed_coverage_matches_the_triangle_area():
    smooth = _mask(TRIANGLE, True)
    area = sum(smooth) / 255
    assert area == pytest.approx(30 * 25 / 2, rel=0.01)
