"""Os motores de traço arredondam para o byte mais próximo; não truncam.

Até 2026-10-02 o depósito de tinta do Lápis e do Nanquim convertia com `static_cast<uint8_t>`, que
trunca. Medido num traço opaco de cor (200, 120, 60) sobre camada transparente, com a caneta indo e
voltando seis vezes pela mesma linha:

                      antes                 depois
  Lápis, fluxo 100%   alfa 254, cor +-1     alfa 255, cor exata
  Lápis, fluxo 5%     alfa 232 (91%)        alfa 244 (96%)
  Nanquim, igual ao Lápis nos dois casos.

Cada depósito perdia em média meio nível; empilhar tinta fazia a cor derivar para baixo e o alfa
parar antes do que a conta pede. O Pincel Redondo já arredondava (mistura linear) e serve de
referência: os três têm que se comportar igual nesta propriedade.

A Borracha trunca de propósito (o alfa tem que chegar a 0): `test_the_eraser_still_clears_to_zero`.
"""

from __future__ import annotations

import numpy as np
import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

W, H = 160, 60
INK = (200, 120, 60)
INK_ENGINES = ["Brush", "Pencil", "Inker"]


def _paint(name, flow, sweeps=6, opaque_base=False, color=INK):
    engine = native.PaintEngineFacade(W, H)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    if opaque_base:  # uma faixa branca opaca larga sob o traço
        engine.set_engine_type(int(native.EngineType.Brush))
        base = engine.get_brush_profile()
        base.brush_size, base.hardness, base.opacity, base.flow = 40.0, 1.0, 1.0, 1.0
        base.base_color = native.ColorRGBA(255, 255, 255, 255)
        engine.begin_stroke_raw(10.0, 30.0, 0.9, 1.0)
        engine.update_stroke_raw(150.0, 30.0, 0.9, 1.5)
        engine.end_stroke_raw()
    engine.set_engine_type(int(getattr(native.EngineType, name)))
    profile = engine.get_brush_profile()
    profile.brush_size = 18.0
    profile.hardness = 1.0
    profile.opacity = 1.0
    profile.flow = flow
    profile.base_color = native.ColorRGBA(*color, 255)
    xs = np.linspace(20.0, 140.0, 40)
    path = []
    for sweep in range(sweeps):
        path += [(float(x), 30.0) for x in (xs if sweep % 2 == 0 else xs[::-1])]
    engine.begin_stroke_raw(path[0][0], path[0][1], 0.9, 1.0)
    for i, (x, y) in enumerate(path[1:], 1):
        engine.update_stroke_raw(x, y, 0.9, 1.0 + 0.008 * i)
    engine.end_stroke_raw()
    pixels = np.frombuffer(bytes(engine.get_layer_pixel_buffer(0)), dtype=np.uint8).reshape(H, W, 4)
    return pixels.astype(int)


def _core(pixels):
    return pixels[28:33, 50:110]


@pytest.mark.parametrize("name", INK_ENGINES)
def test_full_flow_ink_reaches_full_alpha_with_the_exact_color(name):
    core = _core(_paint(name, flow=1.0))
    assert core[:, :, 3].max() == 255, f"{name}: o alfa do miolo parou em {core[:, :, 3].max()}"
    solid = core[core[:, :, 3] == 255][:, :3]
    assert np.abs(solid - np.array(INK)).max() == 0, f"{name}: a cor do miolo derivou do valor pedido"


@pytest.mark.parametrize("name", INK_ENGINES)
def test_low_flow_builds_up_to_within_four_percent_of_full_coverage(name):
    """A 5% de fluxo e 40 passadas a conta pede cobertura total; o limite de 4% é o que cabe em 8 bits."""
    alpha = _paint(name, flow=0.05, sweeps=40)[:, :, 3]
    assert alpha.max() >= round(255 * 0.96) - 1, f"{name}: cobertura máxima {alpha.max() / 255:.1%} (mínimo 96%)"


@pytest.mark.parametrize("name", INK_ENGINES)
def test_overpainting_an_opaque_color_converges_to_it_within_one_level(name):
    """Cor opaca sobre uma base branca opaca, fluxo 30%: o miolo chega na cor pedida a menos de 1 nível.

    Em 8 bits a aproximação para na distância em que `fluxo * diferença` cai abaixo de meio nível
    (0,3 * 1 < 0,5), então 1 nível de sobra é o piso da conta, não deriva.
    """
    core = _core(_paint(name, flow=0.3, sweeps=12, opaque_base=True))
    assert core[:, :, 3].min() == 255
    assert np.abs(core[:, :, :3] - np.array(INK)).max() <= 1, f"{name}: o miolo não convergiu para {INK}"


@pytest.mark.parametrize("name", INK_ENGINES)
def test_full_flow_over_an_opaque_base_is_exactly_the_color(name):
    core = _core(_paint(name, flow=1.0, sweeps=2, opaque_base=True))
    assert np.abs(core[:, :, :3] - np.array(INK)).max() == 0


def test_the_eraser_still_clears_to_zero():
    """Truncar é o certo ao apagar: um carimbo fraco repetido não pode deixar alfa fantasma."""
    engine = native.PaintEngineFacade(W, H)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    engine.set_background_color(255, 255, 255, 255)
    engine.set_engine_type(int(native.EngineType.Eraser))
    profile = engine.get_brush_profile()
    profile.brush_size = 18.0
    profile.hardness = 1.0
    profile.opacity = 1.0
    profile.flow = 0.15
    xs = np.linspace(20.0, 140.0, 40)
    path = [(float(x), 30.0) for sweep in range(40) for x in (xs if sweep % 2 == 0 else xs[::-1])]
    engine.begin_stroke_raw(path[0][0], path[0][1], 0.9, 1.0)
    for i, (x, y) in enumerate(path[1:], 1):
        engine.update_stroke_raw(x, y, 0.9, 1.0 + 0.008 * i)
    engine.end_stroke_raw()
    alpha = np.frombuffer(bytes(engine.get_layer_pixel_buffer(0)), dtype=np.uint8).reshape(H, W, 4)[:, :, 3]
    assert alpha[28:33, 50:110].max() == 0, f"sobrou alfa fantasma de {alpha[28:33, 50:110].max()} níveis"
