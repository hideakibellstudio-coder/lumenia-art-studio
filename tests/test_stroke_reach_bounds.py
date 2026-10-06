"""A área suja do traço cobre tudo o que o motor toca, não só o círculo do carimbo.

A aquarela molhada-no-molhado alcança 1,4x o raio do carimbo (`1 + sangramento * água * 0,4`) e o
marcador 1,12x, mas a área suja do segmento era `raio + 2,5`. Três consequências, medidas em
2026-10-02 com uma aquarela de raio 40, sangramento e água em 100%:

  desfazer    o tile vizinho que a mancha alcançava não tinha o "antes" gravado: um traço centrado a
              84 px (tile 0 vai até 127) deixava 200 pixels de tinta que o desfazer não removia;
  tela        a recomposição da região suja parava no raio do carimbo, e o halo externo só aparecia
              no próximo refresh completo: 423 pixels erravam até 60 níveis (raio 40) e 4789 pixels
              até 180 níveis (raio 80) contra a imagem recomposta por inteiro;
  opacidade   a mistura de opacidade só reescrevia os tiles da área suja.

O motor diz quanto alcança (`IBrushEngine::reachScale`) e o orquestrador usa isso no cálculo.
"""

from __future__ import annotations

import numpy as np
import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

W, H = 300, 128  # o tile 0 vai até x=127


def _engine(kind, size, opacity=1.0, bleed=1.0, water=1.0, wetness=1.0):
    engine = native.PaintEngineFacade(W, H)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    engine.set_background_color(255, 255, 255, 255)
    engine.set_engine_type(int(getattr(native.EngineType, kind)))
    profile = engine.get_brush_profile()
    profile.brush_size, profile.hardness, profile.opacity = size, 0.1, opacity
    profile.base_color = native.ColorRGBA(30, 90, 170, 255)
    if kind == "Watercolor":
        profile.watercolor_params.water_level, profile.watercolor_params.pigment_bleed = water, bleed
    elif kind == "Marker":
        profile.marker_params.solvent_wetness = wetness
    return engine


def _dab_at(engine, x, y=64.0):
    engine.begin_stroke_raw(x, y, 0.9, 1.0)
    engine.update_stroke_raw(x + 0.5, y, 0.9, 9.0)
    engine.end_stroke_raw()


def _alpha(engine):
    return np.frombuffer(bytes(engine.get_layer_pixel_buffer(0)), dtype=np.uint8).reshape(H, W, 4)[:, :, 3]


def _shown(engine):
    return np.frombuffer(bytes(engine.get_pixel_buffer()), dtype=np.uint8).reshape(H, W, 4).astype(int)


def _recomposited(engine):
    """A imagem composta do zero: trocar uma opção de render recompõe a tela inteira."""
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=True)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    return _shown(engine)


# ── 1. Desfazer e refazer ───────────────────────────────────────────────────

@pytest.mark.parametrize("opacity", [1.0, 0.5])
def test_undo_removes_every_pixel_of_a_wet_wash_that_crosses_a_tile_border(opacity):
    """Raio 40 centrado a 84: o círculo termina em 124 (tile 0), a mancha úmida chega a 140 (tile 1)."""
    engine = _engine("Watercolor", size=80.0, opacity=opacity)
    _dab_at(engine, 84.0)
    assert (_alpha(engine)[:, 128:] > 0).any(), "a sonda não cruzou a borda do tile (teste sem força)"
    assert engine.undo()
    assert int((_alpha(engine) > 0).sum()) == 0, "o desfazer deixou tinta para trás"


def test_redo_restores_the_wash_exactly():
    engine = _engine("Watercolor", size=80.0)
    _dab_at(engine, 84.0)
    painted = bytes(engine.get_layer_pixel_buffer(0))
    assert engine.undo() and engine.redo()
    assert bytes(engine.get_layer_pixel_buffer(0)) == painted


# ── 2. A tela mostra o que foi pintado ──────────────────────────────────────

@pytest.mark.parametrize("kind,size", [("Watercolor", 80.0), ("Watercolor", 160.0), ("Marker", 160.0)])
def test_the_shown_image_already_has_the_outer_halo(kind, size):
    """O que a tela mostra logo após o traço é igual ao que uma recomposição completa daria."""
    engine = _engine(kind, size=size)
    _dab_at(engine, 100.0)
    shown = _shown(engine)
    assert np.abs(shown - _recomposited(engine)).max() == 0, f"{kind} raio {size / 2:.0f}: a borda externa da mancha não foi recomposta"


def test_a_plain_brush_keeps_its_exact_dirty_area():
    """O Pincel não alcança além do raio: a área suja continua a mesma de sempre."""
    engine = _engine("Brush", size=80.0)
    _dab_at(engine, 100.0)
    assert np.abs(_shown(engine) - _recomposited(engine)).max() == 0
