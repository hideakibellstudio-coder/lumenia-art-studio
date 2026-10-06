"""Marcador e Aquarela deixam a cor que o artista escolheu; carimbo sobre carimbo não escurece o traço.

Até 2026-10-02 cada carimbo compunha sobre o resultado do anterior, como se fosse papel:

  Marcador   o miolo de um traço azul (30, 90, 170) numa camada vazia saía (21, 63, 123), 30% mais
             escuro (o piso de 70% era alcançado em poucos carimbos), e sobre papel branco o mesmo
             traço quase não tingia: (101, 130, 181) com fluxo 100%;
  Aquarela   o pigmento filtrava o filtrado: o mesmo azul saía (5, 18, 59) na Diluída e (2, 7, 27) na
             Concentrada, quase preto.

Agora a cor sai da base do traço (o pixel antes do primeiro carimbo) e da cobertura que o traço já
alcançou (`StrokeInkLedger`): o miolo tem a cor da tinta, uma vez só, e só um traço novo por cima
multiplica de novo. O alfa acumula como sempre.
"""

from __future__ import annotations

import numpy as np
import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

W, H = 320, 80
INKS = [(30, 90, 170), (200, 60, 50), (240, 200, 60)]
MARKERS = {
    "Copic": dict(size=24.0, hardness=0.8, spacing=0.04, wet=0.6, edge=0.3, flow=0.7),
    "Permanente": dict(size=18.0, hardness=0.9, spacing=0.04, wet=0.1, edge=0.3, flow=0.95),
}
WASHES = {
    "Diluida": dict(size=32.0, hardness=0.3, spacing=0.08, water=0.8, bleed=0.8, fringe=0.3, gran=0.4, flow=0.65),
    "Concentrada": dict(size=22.0, hardness=0.7, spacing=0.06, water=0.3, bleed=0.2, fringe=0.7, gran=0.3, flow=0.85),
    "Veladura": dict(size=40.0, hardness=0.2, spacing=0.08, water=0.5, bleed=0.3, fringe=0.5, gran=0.2, flow=0.4),
}
ALL_PRESETS = [("Marker", name, p) for name, p in MARKERS.items()] + [("Watercolor", name, p) for name, p in WASHES.items()]
IDS = [f"{kind}-{name}" for kind, name, _ in ALL_PRESETS]


def _engine(white_paper=False):
    engine = native.PaintEngineFacade(W, H)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    engine.set_background_color(255, 255, 255, 255)
    if white_paper:  # uma faixa branca opaca larga sob o traço
        engine.set_engine_type(int(native.EngineType.Brush))
        base = engine.get_brush_profile()
        base.brush_size, base.hardness, base.opacity, base.flow = 70.0, 1.0, 1.0, 1.0
        base.base_color = native.ColorRGBA(255, 255, 255, 255)
        _stroke(engine, [(0.0, 40.0), (320.0, 40.0)])
    return engine


def _select(engine, kind, preset, color, flow=None):
    engine.set_engine_type(int(getattr(native.EngineType, kind)))
    profile = engine.get_brush_profile()
    profile.opacity = 1.0
    profile.flow = preset["flow"] if flow is None else flow
    profile.base_color = native.ColorRGBA(*color, 255)
    profile.brush_size, profile.hardness, profile.spacing_factor = preset["size"], preset["hardness"], preset["spacing"]
    if kind == "Marker":
        profile.marker_params.solvent_wetness, profile.marker_params.edge_darkening = preset["wet"], preset["edge"]
    else:
        wash = profile.watercolor_params
        wash.water_level, wash.pigment_bleed = preset["water"], preset["bleed"]
        wash.fringe_intensity, wash.granulation = preset["fringe"], preset["gran"]
    return profile


def _stroke(engine, points, pressure=0.9):
    engine.begin_stroke_raw(points[0][0], points[0][1], pressure, 1.0)
    for i, (x, y) in enumerate(points[1:], 1):
        engine.update_stroke_raw(x, y, pressure, 1.0 + 8.0 * i)
    engine.end_stroke_raw()


def _hline(y=40.0, x0=20.0, x1=300.0, count=140):
    return [(x0 + (x1 - x0) * i / (count - 1), y) for i in range(count)]


def _to_and_fro(sweeps=6, y=40.0):
    """Vai e volta sobre a mesma linha: cada pixel do miolo recebe centenas de carimbos."""
    xs = np.linspace(30.0, 290.0, 80)
    path = []
    for sweep in range(sweeps):
        path += [(float(x), y) for x in (xs if sweep % 2 == 0 else xs[::-1])]
    return path


def _layer(engine):
    return np.frombuffer(bytes(engine.get_layer_pixel_buffer(0)), dtype=np.uint8).reshape(H, W, 4).astype(int)


def _core(pixels):
    """Os pixels do miolo do traço (alfa perto do máximo) no trecho reto do meio."""
    band = pixels[36:45, 90:230]
    solid = band[:, :, 3] >= band[:, :, 3].max() * 0.95
    return band[solid]


# ── 1. Sobre camada vazia: a cor do miolo é a cor escolhida ─────────────────

@pytest.mark.parametrize("kind,name,preset", ALL_PRESETS, ids=IDS)
@pytest.mark.parametrize("ink", INKS)
def test_the_core_of_a_stroke_on_an_empty_layer_has_exactly_the_chosen_color(kind, name, preset, ink):
    engine = _engine()
    _select(engine, kind, preset, ink)
    _stroke(engine, _hline())
    core = _core(_layer(engine))
    assert core.size > 0
    error = np.abs(core[:, :3] - np.array(ink)).max()
    assert error <= 1, f"{kind}/{name}: o miolo saiu {tuple(core[:, :3].mean(axis=0).round())} em vez de {ink} (erro {error})"


@pytest.mark.parametrize("kind,name,preset", ALL_PRESETS, ids=IDS)
def test_dabs_piling_up_in_one_stroke_do_not_darken_it(kind, name, preset):
    """Seis idas e voltas pelo mesmo caminho: a cor do miolo é a do traço de uma passada só."""
    ink = INKS[0]
    once, many = _engine(), _engine()
    for engine, path in ((once, _hline()), (many, _to_and_fro())):
        _select(engine, kind, preset, ink)
        _stroke(engine, path)
    for engine in (once, many):
        error = np.abs(_core(_layer(engine))[:, :3] - np.array(ink)).max()
        assert error <= 1, f"{kind}/{name}: a cor do miolo derivou {error} níveis do valor escolhido"


# ── 2. Sobre papel branco opaco ─────────────────────────────────────────────

@pytest.mark.parametrize("name", MARKERS)
@pytest.mark.parametrize("ink", INKS)
def test_a_marker_stroke_on_white_paper_reaches_the_chosen_color(name, ink):
    engine = _engine(white_paper=True)
    _select(engine, "Marker", MARKERS[name], ink, flow=1.0)
    _stroke(engine, _hline())
    core = _core(_layer(engine))
    assert core[:, 3].min() == 255
    error = np.abs(core[:, :3] - np.array(ink)).max()
    assert error <= 2, f"Marker/{name}: sobre papel branco o miolo saiu {tuple(core[:, :3].mean(axis=0).round())} em vez de {ink}"


@pytest.mark.parametrize("name", WASHES)
@pytest.mark.parametrize("ink", INKS)
def test_a_wash_on_white_paper_is_the_pigment_at_most_thinned_by_water(name, ink):
    """A água só clareia: cada canal fica entre o pigmento e o branco, nunca mais escuro que o pigmento."""
    engine = _engine(white_paper=True)
    _select(engine, "Watercolor", WASHES[name], ink, flow=1.0)
    _stroke(engine, _hline())
    core = _core(_layer(engine))[:, :3]
    assert (core >= np.array(ink) - 1).all(), f"Watercolor/{name}: o miolo escureceu além do pigmento {ink}"
    assert core.max() <= 255


def test_the_wash_thins_with_the_water_level():
    """Mesmo pigmento e fluxo: mais água, miolo mais claro."""
    def core_luma(water):
        engine = _engine(white_paper=True)
        preset = dict(WASHES["Concentrada"], water=water)
        _select(engine, "Watercolor", preset, INKS[0], flow=1.0)
        _stroke(engine, _hline())
        return _core(_layer(engine))[:, :3].mean()

    assert core_luma(0.1) < core_luma(0.9)


# ── 3. Um traço novo por cima multiplica de novo ────────────────────────────

@pytest.mark.parametrize("kind,name,preset", ALL_PRESETS, ids=IDS)
def test_a_second_stroke_over_the_first_darkens_the_crossing(kind, name, preset):
    engine = _engine()
    _select(engine, kind, preset, INKS[0], flow=1.0)
    _stroke(engine, _hline(y=40.0))
    _select(engine, kind, preset, INKS[2], flow=1.0)  # amarelo cruzando o azul
    _stroke(engine, [(160.0, 8.0 + i * 0.6) for i in range(110)])
    pixels = _layer(engine)
    crossing = pixels[38:43, 156:164, :3].reshape(-1, 3).mean(axis=0)
    yellow_alone = pixels[12:20, 156:164, :3].reshape(-1, 3).mean(axis=0)
    assert crossing.sum() < yellow_alone.sum() - 60, f"{kind}/{name}: o cruzamento não escureceu ({crossing.round()} contra {yellow_alone.round()})"
    assert crossing.min() > 10, f"{kind}/{name}: o cruzamento virou preto"


# ── 4. A memória é de um traço só ───────────────────────────────────────────

@pytest.mark.parametrize("kind,name,preset", ALL_PRESETS, ids=IDS)
def test_the_memory_of_one_stroke_does_not_leak_into_the_next(kind, name, preset):
    """Desfazer e pintar outra cor no mesmo lugar: o miolo é a cor nova, sem rastro da anterior."""
    engine = _engine()
    _select(engine, kind, preset, INKS[1])
    _stroke(engine, _hline())
    assert engine.undo()
    _select(engine, kind, preset, INKS[0])
    _stroke(engine, _hline())
    error = np.abs(_core(_layer(engine))[:, :3] - np.array(INKS[0])).max()
    assert error <= 1, f"{kind}/{name}: o traço novo herdou a base do anterior (erro {error})"


# ── 5. Alpha Lock e seleção ─────────────────────────────────────────────────

@pytest.mark.parametrize("name", MARKERS)
def test_alpha_lock_tints_the_pixels_and_keeps_their_alpha(name):
    engine = _engine(white_paper=True)
    base = _layer(engine)
    engine.set_layer_alpha_lock(0, True)
    _select(engine, "Marker", MARKERS[name], INKS[0], flow=1.0)
    _stroke(engine, _hline())
    got = _layer(engine)
    assert np.array_equal(got[:, :, 3], base[:, :, 3]), "a trava de alfa mudou o alfa"
    core = got[36:45, 90:230, :3].reshape(-1, 3)
    assert np.abs(core - np.array(INKS[0])).max() <= 2, "o marcador não tingiu o miolo com a cor escolhida"


@pytest.mark.parametrize("kind,name,preset", ALL_PRESETS, ids=IDS)
def test_selection_still_limits_the_glaze(kind, name, preset):
    engine = _engine()
    assert engine.select_rect(0, 0, 160, H, mode=0)
    _select(engine, kind, preset, INKS[0])
    _stroke(engine, _hline())
    alpha = _layer(engine)[:, :, 3]
    assert alpha[:, :158].max() > 0 and alpha[:, 190:].max() == 0
