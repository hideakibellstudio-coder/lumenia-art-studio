"""O grão do pincel pode ficar preso à tela, como o grão do papel, em vez de acompanhar cada carimbo.

Até 2026-10-02 a textura de altura do pincel era sempre móvel: lida em coordenadas do carimbo, girava e escalava
com ele. Com dezenas de carimbos se sobrepondo por centímetro de traço, cada um traz um grão diferente e o dente do
grafite se borra numa média lisa (o grão do papel, esse sim fixo, era o único que aparecia). Medido com dois
carimbos de 80 px deslocados (10, 3) px, grão de ruído, escala 3, contraste 2, pressão 0,5: na área comum os dois
deixavam o mesmo alfa em 36% dos pixels no modo móvel (Pincel 35,7%, Lápis 36,7%) e em 100% no fixo. Num traço
de 280 px com pincel de 40 px, pressão 0,45, contraste 1, o miolo do traço móvel ficou todo em alfa 255 (desvio
0,0: os grãos de cada carimbo se cobrem uns aos outros) e o fixo manteve o dente (desvio 119,0 no Pincel, 120,4 no
Lápis). A conta do grão estava escrita duas vezes, no Pincel e no Lápis; agora é uma só, com o modo Móvel (o de
sempre) e o modo Fixo.
"""

from __future__ import annotations

import numpy as np
import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

W, H = 300, 300
SIZE = 80.0
GRAINY = [native.EngineType.Brush, native.EngineType.Pencil]


def _engine(engine_type, mode, width, height, size, contrast):
    engine = native.PaintEngineFacade(width, height)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    engine.set_background_color(255, 255, 255, 255)
    engine.set_engine_type(int(engine_type))
    engine.set_brush_height_preset(3)  # ruído
    profile = engine.get_brush_profile()
    profile.brush_size, profile.hardness, profile.opacity = size, 1.0, 1.0
    profile.pressure_size_enabled = False  # o raio é size/2 com qualquer pressão; a pressão só dosa a tinta
    profile.pressure_flow_enabled = False
    profile.base_color = native.ColorRGBA(30, 30, 40, 255)
    profile.brush_grain_enabled = True
    profile.brush_grain_scale = 3.0
    profile.brush_grain_contrast = contrast
    profile.brush_grain_mode = mode
    return engine


def _alpha(engine, width, height):
    return np.frombuffer(bytes(engine.get_layer_pixel_buffer(0)), dtype=np.uint8).reshape(height, width, 4)[:, :, 3].astype(int)


def _stamp(engine_type, mode, center, angle=0.0, pressure=0.5):
    """O alfa da camada depois de UM carimbo de 80 px no centro dado."""
    engine = _engine(engine_type, mode, W, H, SIZE, 2.0)
    engine.get_brush_profile().tip.angle = angle
    engine.begin_stroke_raw(center[0], center[1], pressure, 1.0)
    engine.end_stroke_raw()
    return _alpha(engine, W, H)


def _stroke(engine_type, mode):
    """O alfa de um traço reto de 280 px, pincel de 40 px: carimbos se sobrepondo como no uso real."""
    engine = _engine(engine_type, mode, 400, 120, 40.0, 1.0)
    engine.begin_stroke_raw(40.0, 60.0, 0.45, 1.0)
    for i, x in enumerate(range(44, 361, 4), 1):
        engine.update_stroke_raw(float(x), 60.0, 0.45, 1.0 + 8.0 * i)
    engine.end_stroke_raw()
    return _alpha(engine, 400, 120)


def _inside_both(first, second):
    """Os pixels bem dentro dos dois carimbos (longe da borda de cada um, onde a forma já não pesa)."""
    ys, xs = np.mgrid[0:H, 0:W]
    near = lambda c: (xs + 0.5 - c[0]) ** 2 + (ys + 0.5 - c[1]) ** 2 < (0.7 * SIZE / 2) ** 2
    return near(first) & near(second)


@pytest.mark.parametrize("engine_type", GRAINY, ids=lambda e: e.name)
def test_default_is_the_moving_grain(engine_type):
    profile = native.PaintEngineFacade(32, 32).get_brush_profile()
    assert profile.brush_grain_mode == native.GrainMode.Moving


@pytest.mark.parametrize("engine_type", GRAINY, ids=lambda e: e.name)
def test_the_fixed_grain_is_the_same_at_the_same_pixel_from_any_stamp(engine_type):
    """Dois carimbos deslocados deixam EXATAMENTE o mesmo alfa onde se sobrepõem: o grão é do pixel."""
    first, second = (150.0, 150.0), (160.0, 153.0)
    a = _stamp(engine_type, native.GrainMode.Fixed, first)
    b = _stamp(engine_type, native.GrainMode.Fixed, second)
    area = _inside_both(first, second)
    assert np.array_equal(a[area], b[area])
    assert a[area].std() > 15, "o grão quase não aparece: o teste não prova nada"


@pytest.mark.parametrize("engine_type", GRAINY, ids=lambda e: e.name)
def test_the_moving_grain_travels_with_the_stamp(engine_type):
    """No modo móvel o grão anda junto: o padrão do segundo carimbo é o do primeiro deslocado de (10, 3) px."""
    a = _stamp(engine_type, native.GrainMode.Moving, (150.0, 150.0))
    b = _stamp(engine_type, native.GrainMode.Moving, (160.0, 153.0))
    assert np.array_equal(a[80:220, 80:200], b[83:223, 90:210])
    area = _inside_both((150.0, 150.0), (160.0, 153.0))
    assert (a[area] == b[area]).mean() < 0.5, "o grão móvel não deveria coincidir no mesmo pixel"


@pytest.mark.parametrize("engine_type", GRAINY, ids=lambda e: e.name)
def test_the_fixed_grain_does_not_turn_with_the_tip(engine_type):
    """Girar a ponta gira o grão móvel e não mexe no fixo."""
    center = (150.0, 150.0)
    fixed_0 = _stamp(engine_type, native.GrainMode.Fixed, center, angle=0.0)
    fixed_40 = _stamp(engine_type, native.GrainMode.Fixed, center, angle=40.0)
    moving_0 = _stamp(engine_type, native.GrainMode.Moving, center, angle=0.0)
    moving_40 = _stamp(engine_type, native.GrainMode.Moving, center, angle=40.0)
    area = _inside_both(center, center)
    assert np.array_equal(fixed_0[area], fixed_40[area])
    assert not np.array_equal(moving_0[area], moving_40[area])


@pytest.mark.parametrize("engine_type", GRAINY, ids=lambda e: e.name)
def test_a_stroke_keeps_the_tooth_only_with_the_fixed_grain(engine_type):
    """O ganho de verdade: com os carimbos se sobrepondo o grão móvel se apaga, o fixo continua aparecendo."""
    core = (slice(50, 70), slice(100, 300))
    moving = _stroke(engine_type, native.GrainMode.Moving)[core]
    fixed = _stroke(engine_type, native.GrainMode.Fixed)[core]
    assert moving.std() < 5, "o grão móvel já aparecia no traço: a premissa do teste mudou"
    assert fixed.std() > 60
    assert fixed.min() < 30 < 225 < fixed.max(), "o fixo deveria ter dentes vazios e picos cheios"


@pytest.mark.parametrize("engine_type", GRAINY, ids=lambda e: e.name)
def test_the_two_modes_draw_different_grain(engine_type):
    center = (150.0, 150.0)
    assert not np.array_equal(_stamp(engine_type, native.GrainMode.Moving, center),
                              _stamp(engine_type, native.GrainMode.Fixed, center))


def test_the_interface_converts_the_combo_index_and_refuses_one_out_of_range():
    from ui.infrastructure.bridge_client.brush_param_table import to_grain_mode

    assert to_grain_mode(1, native) == native.GrainMode.Fixed
    with pytest.raises(ValueError):
        to_grain_mode(2, native)
