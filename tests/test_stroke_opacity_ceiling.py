"""Opacidade é o TETO do traço; fluxo é quanto cada carimbo deposita.

Antes de 2026-10-02 só existia "opacidade", e ela valia por carimbo: um Pincel Redondo a
20/30/50% de opacidade chegava a 92/98/100% de alfa onde os carimbos se sobrepõem (espaçamento
de 8% do diâmetro), então a opacidade nunca limitava nada. Agora:

  `flow`     o que cada carimbo deposita (acumula; é o que "opacidade" era);
  `opacity`  o máximo que o TRAÇO inteiro pode cobrir: o motor pinta numa cópia de trabalho da
             camada e, a cada segmento, a camada recebe a mistura base <-> trabalho por esse fator.

A mistura é genérica: vale para todos os mini-motores (a borracha apaga no máximo `opacity`, o
borrar arrasta no máximo `opacity`), então a propriedade medida aqui é a mesma para os nove:
resultado(opacity) == mistura(base, resultado(opacity=1), opacity), com a conta em alfa
pré-multiplicado.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

W, H = 160, 60
ENGINES = ["Brush", "Pencil", "Inker", "Eraser", "Marker", "Blur", "Smudge", "Watercolor", "OilImpasto"]


def _engine():
    engine = native.PaintEngineFacade(W, H)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    engine.set_background_color(255, 255, 255, 255)
    return engine


def _stroke(engine, points, pressure=0.9):
    x0, y0 = points[0]
    engine.begin_stroke_raw(x0, y0, pressure, 1.0)
    for i, (x, y) in enumerate(points[1:], 1):
        engine.update_stroke_raw(x, y, pressure, 1.0 + 0.008 * i)
    engine.end_stroke_raw()


def _to_and_fro(y=30.0, sweeps=3):
    """Vai e volta sobre a mesma linha: cada pixel do miolo recebe dezenas de carimbos."""
    xs = np.linspace(20.0, 140.0, 40)
    path = []
    for s in range(sweeps):
        path += [(float(x), y) for x in (xs if s % 2 == 0 else xs[::-1])]
    return path


def _layer(engine) -> np.ndarray:
    return np.frombuffer(bytes(engine.get_layer_pixel_buffer(0)), dtype=np.uint8).reshape(H, W, 4).astype(float)


def _configure(engine, name, opacity, flow=1.0):
    engine.set_engine_type(int(getattr(native.EngineType, name)))
    profile = engine.get_brush_profile()
    profile.brush_size = 16.0
    profile.hardness = 0.9
    profile.opacity = opacity
    profile.flow = flow
    profile.base_color = native.ColorRGBA(20, 30, 90, 255)
    return profile


BASE_BAND = (210, 120, 60)
BASE_COLUMN = (40, 90, 200)


def _base_painted(engine):
    """Camada 0 com uma faixa larga de cor cruzada por uma coluna de outra cor.

    O Desfoque e o Borrar só têm o que fazer onde há borda de cor: numa faixa lisa eles não
    mudam nada (até 2026-10-02 pareciam mudar, por 1 nível de ruído do truncamento).
    """
    _configure(engine, "Brush", 1.0)
    engine.get_brush_profile().brush_size = 40.0
    engine.get_brush_profile().base_color = native.ColorRGBA(*BASE_BAND, 255)
    _stroke(engine, [(10.0, 30.0), (150.0, 30.0)])
    engine.get_brush_profile().brush_size = 16.0
    engine.get_brush_profile().base_color = native.ColorRGBA(*BASE_COLUMN, 255)
    _stroke(engine, [(80.0, 4.0), (80.0, 56.0)])


# ── 1. A sonda de produto: a opacidade limita o traço ───────────────────────

@pytest.mark.parametrize("opacity", [0.2, 0.3, 0.5, 0.8])
def test_opacity_caps_the_stroke_where_dabs_overlap(opacity):
    engine = _engine()
    _configure(engine, "Brush", opacity)
    _stroke(engine, _to_and_fro())
    alpha = _layer(engine)[:, :, 3]
    ceiling = round(opacity * 255)
    assert alpha.max() <= ceiling + 1, (
        f"opacidade {opacity:.0%}: alfa chegou a {alpha.max() / 255:.0%} (teto {ceiling / 255:.0%}); "
        f"a opacidade não limita o traço"
    )
    assert alpha[28:33, 40:120].mean() >= ceiling - 2, "o miolo do traço deveria chegar ao teto"


def test_flow_still_builds_up_under_the_ceiling():
    """Fluxo baixo + opacidade 100%: cada passada soma, como a opacidade antiga fazia."""
    engine = _engine()
    _configure(engine, "Brush", 1.0, flow=0.05)
    _stroke(engine, _to_and_fro(sweeps=1))
    one_pass = _layer(engine)[30, 80, 3]
    engine = _engine()
    _configure(engine, "Brush", 1.0, flow=0.05)
    _stroke(engine, _to_and_fro(sweeps=3))
    three_passes = _layer(engine)[30, 80, 3]
    assert 0 < one_pass < three_passes <= 255


def test_full_opacity_takes_the_direct_path():
    """Opacidade 1.0 não cria cópia nem mistura: o resultado é o do pincel sem teto."""
    a, b = _engine(), _engine()
    _configure(a, "Brush", 1.0)
    _configure(b, "Brush", 1.0)
    for e in (a, b):
        _stroke(e, _to_and_fro())
    assert bytes(a.get_layer_pixel_buffer(0)) == bytes(b.get_layer_pixel_buffer(0))


# ── 2. A propriedade geral: vale para os nove motores ───────────────────────

def _premult_mix(base: np.ndarray, full: np.ndarray, opacity: float) -> np.ndarray:
    def premult(px):
        out = px.copy()
        out[:, :, :3] = px[:, :, :3] * px[:, :, 3:4] / 255.0
        return out

    mixed = premult(base) + (premult(full) - premult(base)) * opacity
    alpha = mixed[:, :, 3:4]
    rgb = np.where(alpha > 0, mixed[:, :, :3] * 255.0 / np.maximum(alpha, 1e-9), 0.0)
    return np.concatenate([rgb, alpha], axis=2)


@pytest.mark.parametrize("name", ENGINES)
def test_stroke_opacity_is_a_mix_of_the_base_and_the_full_result(name):
    results = {}
    for opacity in (1.0, 0.5):
        engine = _engine()
        _base_painted(engine)
        base = _layer(engine)
        _configure(engine, name, opacity)
        _stroke(engine, _to_and_fro(y=24.0, sweeps=2))
        results[opacity] = _layer(engine)
    expected = _premult_mix(base, results[1.0], 0.5)
    got = results[0.5]
    changed = np.abs(results[1.0] - base).max(axis=2) > 0
    assert changed.any(), f"{name}: o traço de referência não mudou nada (teste sem força)"
    # Onde o alfa é ~0 a cor não tem significado; compara cor só onde há alfa nos dois.
    visible = (expected[:, :, 3] > 8) & (got[:, :, 3] > 8)
    alpha_error = np.abs(got[:, :, 3] - expected[:, :, 3]).max()
    color_error = np.abs(got[:, :, :3] - expected[:, :, :3])[visible].max() if visible.any() else 0.0
    assert alpha_error <= 1.01 and color_error <= 3.01, (
        f"{name}: a opacidade 50% difere da mistura (alfa {alpha_error:.1f}, cor {color_error:.1f} níveis)"
    )


# ── 3. Histórico, trava de alfa e seleção ───────────────────────────────────

def test_undo_and_redo_restore_the_mixed_stroke_exactly():
    engine = _engine()
    _base_painted(engine)
    before = bytes(engine.get_layer_pixel_buffer(0))
    _configure(engine, "Brush", 0.4)
    _stroke(engine, _to_and_fro(y=24.0))
    after = bytes(engine.get_layer_pixel_buffer(0))
    assert after != before
    assert engine.undo() and bytes(engine.get_layer_pixel_buffer(0)) == before
    assert engine.redo() and bytes(engine.get_layer_pixel_buffer(0)) == after


def test_alpha_lock_keeps_the_alpha_and_caps_the_color_change():
    engine = _engine()
    _base_painted(engine)
    engine.set_layer_alpha_lock(0, True)
    base = _layer(engine)
    _configure(engine, "Brush", 0.5)
    _stroke(engine, _to_and_fro(y=24.0))
    got = _layer(engine)
    assert np.array_equal(got[:, :, 3], base[:, :, 3]), "a trava de alfa mudou o alfa"
    painted = (base[:, :, 3] > 0) & (np.abs(got - base).max(axis=2) > 0)
    assert painted.any()
    ink = np.array([20.0, 30.0, 90.0])
    # Cada canal fica entre a base e a tinta: nunca passa do que 100% pintaria.
    low = np.minimum(base[:, :, :3], ink) - 1.5
    high = np.maximum(base[:, :, :3], ink) + 1.5
    assert ((got[:, :, :3] >= low) & (got[:, :, :3] <= high))[painted].all()
    moved = np.abs(got[:, :, :3] - base[:, :, :3]).max(axis=2)
    ceiling = 0.5 * np.abs(ink - base[:, :, :3]).max(axis=2) + 2
    assert (moved <= ceiling)[painted].all(), "a cor passou do teto de 50% em algum pixel"


def test_selection_still_limits_a_capped_stroke():
    engine = _engine()
    assert engine.select_rect(0, 0, 80, H, mode=0)
    _configure(engine, "Brush", 0.5)
    _stroke(engine, _to_and_fro())
    alpha = _layer(engine)[:, :, 3]
    assert alpha[:, :80].max() > 0 and alpha[:, 82:].max() == 0
    assert math.isclose(alpha[:, :80].max(), 128, abs_tol=2)
