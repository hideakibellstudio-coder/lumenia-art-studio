"""Balde e varinha: a opção "Todas as Camadas" decide de onde vem a região.

Até 2026-09-25 só a varinha respeitava a opção; o balde lia sempre a imagem
composta, e desmarcar a caixa na barra do balde não mudava nada. Os dois agora
usam `LayerSampleSource` (motor, `boundary/orchestrator`). Cena: um quadrado
vermelho na camada de baixo e a camada de cima, vazia, ativa.
"""
from __future__ import annotations

import pytest

native = pytest.importorskip("aladyn_engine_native")

L = 40
SQUARE = (10, 10, 12, 12)  # x, y, largura, altura
INSIDE, OUTSIDE = (15, 15), (2, 2)


def _scene():
    facade = native.PaintEngineFacade(L, L)
    x, y, w, h = SQUARE
    assert facade.paste_rgba_buffer_on_active_layer(x, y, w, h, bytes([220, 20, 20, 255]) * (w * h))
    top = facade.add_layer("Cima", -1)
    assert facade.select_layer(top)
    return facade, top


def _alpha(buffer: bytes, point: tuple[int, int]) -> int:
    x, y = point
    return buffer[(y * L + x) * 4 + 3]


@pytest.mark.parametrize("sample_all, fills_outside", [(True, False), (False, True)])
def test_bucket_region_follows_the_sample_all_option(sample_all, fills_outside):
    facade, top = _scene()
    assert facade.flood_fill(*INSIDE, native.ColorRGBA(20, 20, 220, 255), 10, True, 0, sample_all)
    pixels = facade.get_layer_pixel_buffer(top)
    assert _alpha(pixels, INSIDE) == 255
    assert (_alpha(pixels, OUTSIDE) == 255) is fills_outside


@pytest.mark.parametrize("sample_all, selects_outside", [(True, False), (False, True)])
def test_wand_region_follows_the_sample_all_option(sample_all, selects_outside):
    facade, _top = _scene()
    assert facade.magic_wand_select(*INSIDE, 10, True, 0, False, 0, sample_all)
    mask = facade.get_selection_mask_buffer()
    assert mask[INSIDE[1] * L + INSIDE[0]] == 255
    assert (mask[OUTSIDE[1] * L + OUTSIDE[0]] == 255) is selects_outside
