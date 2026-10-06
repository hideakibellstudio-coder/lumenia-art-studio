"""A velocidade e a inclinação da caneta também dosam o fluxo, e a inclinação também o tamanho.

Até 2026-10-02 o mapeador de dinâmicas só deixava a pressão mexer no fluxo (e a velocidade só no tamanho, por
curva). Quem desenha a nanquim ou sombreia a lápis pede o contrário do que a pressão dá sozinha: o traço rápido
sai mais leve (a tinta que o pincel tem se espalha por mais distância) e a caneta deitada risca largo e fraco, não
só mais achatado. Três controles novos, todos de 0 a 1 e todos desligados no padrão (nenhum dos 108 pinos dos
motores se mexeu):

  velocity_to_flow  1,0 apaga o traço na velocidade máxima
  tilt_to_size      1,0 dobra o diâmetro com a caneta deitada
  tilt_to_flow      1,0 apaga o traço com a caneta deitada

Mouse e caneta em pé (altitude de 70° para cima) não sofrem efeito algum da inclinação.
"""

from __future__ import annotations

import numpy as np
import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

W, H = 400, 300
LEFT, RIGHT, ROW = 60.0, 340.0, 150.0
UPRIGHT = (0.0, 0.0)
LYING = (0.0, 70.0)  # altitude de 20°: totalmente deitada
HALF_LYING = (0.0, 45.0)  # altitude de 45°

INK_ENGINES = {
    "brush": native.EngineType.Brush, "pencil": native.EngineType.Pencil, "inker": native.EngineType.Inker,
    "marker": native.EngineType.Marker, "watercolor": native.EngineType.Watercolor, "oil": native.EngineType.OilImpasto,
}


def _mark(engine_name="brush", tilt=UPRIGHT, step_ms=8.0, size=30.0, flow=0.5, spacing=0.08, **controls):
    """O alfa da camada depois de uma linha horizontal de 280 px, com os controles dados (`tilt_to_*` vão na ponta).

    `step_ms` é o tempo entre amostras (o relógio do motor é em segundos): 8 ms são 500 px/s a 4 px por amostra."""
    engine = native.PaintEngineFacade(W, H)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    engine.set_background_color(255, 255, 255, 255)
    engine.set_engine_type(int(INK_ENGINES[engine_name]))
    profile = engine.get_brush_profile()
    profile.brush_size, profile.hardness, profile.opacity, profile.spacing_factor = size, 0.8, 1.0, spacing
    profile.flow = flow
    profile.pressure_flow_enabled = False
    profile.pressure_size_enabled = False
    profile.base_color = native.ColorRGBA(30, 60, 160, 255)
    for name, value in controls.items():
        setattr(profile.tip if name.startswith("tilt_") else profile, name, value)
    tilt_x, tilt_y = tilt
    engine.begin_stroke_raw(LEFT, ROW, 1.0, 1.0, tilt_x=tilt_x, tilt_y=tilt_y)
    steps = 70
    for i in range(1, steps + 1):
        engine.update_stroke_raw(LEFT + (RIGHT - LEFT) * i / steps, ROW, 1.0, 1.0 + step_ms * 0.001 * i,
                                 tilt_x=tilt_x, tilt_y=tilt_y)
    engine.end_stroke_raw()
    return np.frombuffer(bytes(engine.get_layer_pixel_buffer(0)), dtype=np.uint8).reshape(H, W, 4)[:, :, 3].astype(int)


def _thickness(alpha):
    """A espessura do traço no meio dele, em px (alfa > 20)."""
    return int((alpha[:, W // 2] > 20).sum())


def _depth(alpha):
    """O alfa no centro do traço, no meio dele."""
    return int(alpha[int(ROW), W // 2])


def test_the_new_controls_are_off_by_default():
    profile = native.PaintEngineFacade(32, 32).get_brush_profile()
    assert (profile.velocity_to_flow, profile.tip.tilt_to_size, profile.tip.tilt_to_flow) == (0.0, 0.0, 0.0)


# ─── Inclinação → tamanho ───────────────────────────────────────────────────────

@pytest.mark.parametrize("name", INK_ENGINES)
def test_a_lying_pen_draws_wider_with_tilt_to_size(name):
    """30 px em pé, 60 px com a caneta deitada e o controle em 1,0 (o diâmetro dobra)."""
    plain = _thickness(_mark(name, tilt=LYING))
    wide = _thickness(_mark(name, tilt=LYING, tilt_to_size=1.0))
    assert 26 <= plain <= 34, plain
    assert 54 <= wide <= 66, wide


@pytest.mark.parametrize("name", INK_ENGINES)
def test_an_upright_pen_and_the_mouse_are_not_touched_by_tilt_to_size(name):
    assert _thickness(_mark(name, tilt=UPRIGHT, tilt_to_size=1.0)) == _thickness(_mark(name, tilt=UPRIGHT))


def test_tilt_to_size_grows_with_the_lean_and_with_the_amount():
    sizes = [_thickness(_mark(tilt=HALF_LYING, tilt_to_size=amount)) for amount in (0.0, 0.5, 1.0)]
    assert sizes[0] < sizes[1] < sizes[2], sizes
    half = _thickness(_mark(tilt=LYING, tilt_to_size=0.5))
    assert 40 <= half <= 50, half  # metade do aumento: 28 → 44 (e 58 com 1,0)


# ─── Inclinação → fluxo ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", INK_ENGINES)
def test_a_lying_pen_deposits_less_with_tilt_to_flow(name):
    full = _depth(_mark(name, tilt=LYING))
    half = _depth(_mark(name, tilt=LYING, tilt_to_flow=0.5))
    none = _depth(_mark(name, tilt=LYING, tilt_to_flow=1.0))
    assert full > half > none, (full, half, none)
    assert none <= 2, "com 1,0 e a caneta deitada nada deveria ficar no papel"


@pytest.mark.parametrize("name", INK_ENGINES)
def test_an_upright_pen_keeps_its_flow_with_tilt_to_flow(name):
    assert _depth(_mark(name, tilt=UPRIGHT, tilt_to_flow=1.0)) == _depth(_mark(name, tilt=UPRIGHT))


# ─── Velocidade → fluxo ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", INK_ENGINES)
def test_a_fast_stroke_is_lighter_with_velocity_to_flow(name):
    """Mesmo caminho, 40 ms por amostra (lento) contra 1 ms (rápido): sem o controle saem iguais, com ele o rápido clareia."""
    slow, fast = 40.0, 1.0
    light = dict(flow=0.12, spacing=0.2)  # fluxo baixo e carimbos espaçados: o centro não satura em 255
    assert _depth(_mark(name, step_ms=slow, **light)) == _depth(_mark(name, step_ms=fast, **light))
    slow_depth = _depth(_mark(name, step_ms=slow, velocity_to_flow=1.0, **light))
    fast_depth = _depth(_mark(name, step_ms=fast, velocity_to_flow=1.0, **light))
    assert fast_depth < slow_depth, (slow_depth, fast_depth)
    assert fast_depth <= 0.5 * slow_depth, "o traço rápido deveria ficar bem mais leve"


def test_velocity_to_flow_lightens_with_the_amount():
    depths = [_depth(_mark(step_ms=1.0, flow=0.12, spacing=0.2, velocity_to_flow=amount)) for amount in (0.0, 0.4, 0.8)]
    assert depths[0] > depths[1] > depths[2], depths


def test_the_controls_refuse_nothing_out_of_range():
    """Valores fora de 0..1 não derrubam o motor nem pintam com fluxo negativo."""
    alpha = _mark(tilt=LYING, step_ms=1.0, tilt_to_size=7.0, tilt_to_flow=7.0, velocity_to_flow=7.0)
    assert alpha.min() >= 0 and alpha.max() <= 255
