"""A pressão, a inclinação e o ângulo da ponta moldam o carimbo em TODOS os motores, e o lado do grafite sombreia.

Até 2026-10-02 o interpolador de spline (o caminho de todo traço com 3 ou mais amostras) trocava o ângulo do
carimbo pela tangente do traço, com "seguir o traço" ligado ou não: uma ponta chata de 0° (eixo maior na
horizontal) pintava 6 px de espessura num traço horizontal E num vertical, em vez de 6 e 28; o ângulo da ponta, a
inclinação→ângulo, a pressão→ângulo, a torção e o azimute do lado do grafite nunca chegavam ao corpo do traço.

Além disso o mapeador calculava a elipse dinâmica da ponta (achatamento por pressão e por inclinação) e a
punha no carimbo, mas os oito mini-motores liam só `profile.tip.aspectRatio`, o valor fixo: os dois controles
só funcionavam no motor padrão. E o interruptor "sombreamento por inclinação" do Lápis estava na interface e
em cinco presets sem que nenhuma linha do motor o lesse. Medido numa linha horizontal de 180 px, pincel de 30 px,
altura do traço em px (alfa > 20) com a ponta achatada pela pressão 1,0 (0,8) e com a caneta deitada a 70°
(inclinação → achatamento 1,0):

  Pincel (motor padrão)  30 → 8  e 30 → 8
  Lápis, Nanquim, Marcador, Óleo   30 → 30  e 30 → 30 (a elipse dinâmica era ignorada)
  Aquarela                         34 → 34  e 34 → 34
  Lápis com sombreamento, deitado  30 → 30 (o interruptor não fazia nada)

Agora todos leem a elipse do carimbo, e o lápis deitado risca com o lado do grafite: a marca se alonga no
sentido em que a caneta pende (até três vezes) e deposita menos por área.
"""

from __future__ import annotations

import numpy as np
import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

W, H = 300, 300
LEFT, RIGHT, ROW = 60.0, 240.0, 150.0
UPRIGHT = (0.0, 0.0)
LYING_DOWN = (0.0, 70.0)   # a caneta pende para baixo da tela: azimute 90°
LYING_RIGHT = (70.0, 0.0)  # a caneta pende para a direita: azimute 0°

INK_ENGINES = ["brush", "pencil", "inker", "marker", "watercolor", "oil"]
ENGINE_IDS = {
    "brush": native.EngineType.Brush, "pencil": native.EngineType.Pencil, "inker": native.EngineType.Inker,
    "eraser": native.EngineType.Eraser, "marker": native.EngineType.Marker,
    "watercolor": native.EngineType.Watercolor, "oil": native.EngineType.OilImpasto,
}


def _engine():
    engine = native.PaintEngineFacade(W, H)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    engine.set_background_color(255, 255, 255, 255)
    return engine


def _line(engine, tilt=UPRIGHT, pressure=1.0, vertical=False):
    tilt_x, tilt_y = tilt
    start, end = ((ROW, LEFT), (ROW, RIGHT)) if vertical else ((LEFT, ROW), (RIGHT, ROW))
    engine.begin_stroke_raw(start[0], start[1], pressure, 1.0, tilt_x=tilt_x, tilt_y=tilt_y)
    for i in range(1, 60):
        t = i / 59
        engine.update_stroke_raw(start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t, pressure,
                                 1.0 + 8.0 * i, tilt_x=tilt_x, tilt_y=tilt_y)
    engine.end_stroke_raw()


def _mark(name, tilt=UPRIGHT, pressure=1.0, tilt_to_aspect=0.0, pressure_to_aspect=0.0, shading=False, size=30.0,
          aspect=1.0, angle=0.0, follow=False, tilt_to_angle=0.0, vertical=False):
    """O alfa da camada depois de uma linha horizontal (ou vertical)."""
    engine = _engine()
    engine.set_engine_type(int(ENGINE_IDS[name]))
    profile = engine.get_brush_profile()
    profile.brush_size, profile.hardness, profile.opacity, profile.spacing_factor = size, 0.8, 1.0, 0.08
    profile.base_color = native.ColorRGBA(30, 60, 160, 255)
    profile.tip.tilt_to_aspect = tilt_to_aspect
    profile.tip.tilt_to_angle = tilt_to_angle
    profile.tip.aspect_ratio, profile.tip.angle, profile.tip.follow_stroke = aspect, angle, follow
    profile.pressure_to_aspect = pressure_to_aspect
    profile.pencil_params.tilt_shading_enabled = shading
    _line(engine, tilt, pressure, vertical)
    return np.frombuffer(bytes(engine.get_layer_pixel_buffer(0)), dtype=np.uint8).reshape(H, W, 4)[:, :, 3].copy()


def _extent(alpha):
    """(altura, largura) em px da marca inteira: onde o alfa passa de 20."""
    rows, cols = np.nonzero(alpha > 20)
    return int(rows.max() - rows.min() + 1), int(cols.max() - cols.min() + 1)


def _thickness(alpha, vertical=False):
    """A espessura do traço no MEIO dele, em px (o começo e o fim do traço têm carimbos de outro caminho)."""
    line = alpha[:, int(ROW)] if not vertical else alpha[int(ROW), :]
    return int((line > 20).sum())


# ─── O ângulo da ponta ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", INK_ENGINES)
def test_a_fixed_chisel_keeps_its_angle_in_every_direction(name):
    """Ponta chata de 0° sem seguir o traço: fina num traço horizontal (6 px), larga num vertical (28 px)."""
    across_horizontal = _thickness(_mark(name, aspect=0.2))
    across_vertical = _thickness(_mark(name, aspect=0.2, vertical=True), vertical=True)
    assert across_horizontal <= 12 and across_vertical >= 20, (across_horizontal, across_vertical)


@pytest.mark.parametrize("name", INK_ENGINES)
def test_following_the_stroke_turns_the_chisel_with_it(name):
    """Seguindo o traço o eixo maior corre ao longo dele: 6 px de espessura nos dois sentidos."""
    across_horizontal = _thickness(_mark(name, aspect=0.2, follow=True))
    across_vertical = _thickness(_mark(name, aspect=0.2, follow=True, vertical=True), vertical=True)
    assert across_horizontal <= 12 and across_vertical <= 12, (across_horizontal, across_vertical)


@pytest.mark.parametrize("name", INK_ENGINES)
def test_the_tip_angle_is_an_offset_from_the_stroke_while_following(name):
    """Seguindo o traço com a ponta a 90°, o eixo maior fica atravessado: larga nos dois sentidos."""
    across_horizontal = _thickness(_mark(name, aspect=0.2, angle=90.0, follow=True))
    across_vertical = _thickness(_mark(name, aspect=0.2, angle=90.0, follow=True, vertical=True), vertical=True)
    assert across_horizontal >= 20 and across_vertical >= 20, (across_horizontal, across_vertical)


def test_the_azimuth_turns_the_tip_when_tilt_to_angle_is_on():
    """Caneta pendendo para a direita (azimute 0°) deixa o eixo maior na horizontal: fino; para baixo (90°), alto."""
    right = _thickness(_mark("pencil", tilt=LYING_RIGHT, aspect=0.2, tilt_to_angle=1.0))
    down = _thickness(_mark("pencil", tilt=LYING_DOWN, aspect=0.2, tilt_to_angle=1.0))
    assert right <= 12 and down >= 20, (right, down)


# ─── Pressão e inclinação achatando a ponta ─────────────────────────────────────

@pytest.mark.parametrize("name", INK_ENGINES)
def test_the_pressure_flattens_the_tip_in_every_engine(name):
    """Pressão 1,0 com achatamento 0,8: a altura da linha cai de 30 para 8 px no Pincel e passa a cair nos outros."""
    round_tip, flat_tip = _thickness(_mark(name)), _thickness(_mark(name, pressure_to_aspect=0.8))
    assert flat_tip <= 0.45 * round_tip, f"{name}: {round_tip} → {flat_tip} px, a ponta não achatou"


@pytest.mark.parametrize("name", INK_ENGINES)
def test_a_pen_lying_down_flattens_the_tip_in_every_engine(name):
    """Caneta a 70° com inclinação → achatamento 1,0: a altura cai de 30 para 8 px no Pincel e passa a cair nos outros."""
    upright = _thickness(_mark(name, tilt=UPRIGHT, tilt_to_aspect=1.0))
    lying = _thickness(_mark(name, tilt=LYING_DOWN, tilt_to_aspect=1.0))
    assert lying <= 0.45 * upright, f"{name}: {upright} → {lying} px, a ponta não achatou"


@pytest.mark.parametrize("name", INK_ENGINES)
def test_a_pen_standing_straight_changes_nothing(name):
    """Sem inclinação (mouse, ou caneta em pé) os controles de inclinação não mexem em nenhum pixel."""
    assert np.array_equal(_mark(name), _mark(name, tilt_to_aspect=1.0))


def test_the_eraser_wipes_a_flattened_band():
    """A Borracha apaga uma faixa mais fina quando a pressão achata a ponta (só a Borracha lia a elipse fixa)."""
    def wiped(pressure_to_aspect):
        engine = _engine()
        engine.set_engine_type(int(native.EngineType.Brush))
        profile = engine.get_brush_profile()
        profile.brush_size, profile.hardness, profile.opacity = 160.0, 1.0, 1.0
        profile.base_color = native.ColorRGBA(30, 60, 160, 255)
        engine.begin_stroke_raw(40.0, ROW, 1.0, 1.0)
        for i in range(1, 30):
            engine.update_stroke_raw(40.0 + 220.0 * i / 29, ROW, 1.0, 1.0 + 8.0 * i)
        engine.end_stroke_raw()
        engine.set_engine_type(int(native.EngineType.Eraser))
        profile = engine.get_brush_profile()
        profile.brush_size, profile.hardness, profile.opacity, profile.flow = 40.0, 1.0, 1.0, 1.0
        profile.pressure_to_aspect = pressure_to_aspect
        _line(engine)
        alpha = np.frombuffer(bytes(engine.get_layer_pixel_buffer(0)), dtype=np.uint8).reshape(H, W, 4)[:, :, 3]
        return int((alpha[75:225, 150] < 128).sum())  # só dentro da faixa pintada (linhas 70 a 230)

    assert wiped(0.8) <= 0.45 * wiped(0.0)


def test_the_stroke_preview_shows_the_flattened_tip():
    """A prévia do painel desenha a ponta achatada (a prévia criava carimbos sempre redondos)."""
    def ink(aspect):
        profile = native.BrushProfile()
        profile.brush_size = 40.0
        profile.tip.aspect_ratio = aspect
        pixels = np.frombuffer(native.render_stroke_preview(profile, 260, 52), dtype=np.uint8).reshape(52, 260, 4)
        return int((pixels[:, :, 3] > 20).sum())

    assert ink(0.3) <= 0.75 * ink(1.0)


# ─── O lado do grafite ──────────────────────────────────────────────────────────

def test_the_graphite_side_stretches_the_mark_toward_where_the_pen_leans():
    """Lápis deitado a 70° para baixo: a marca de uma linha horizontal fica mais de 2× mais alta e igualmente larga."""
    upright = _mark("pencil", tilt=UPRIGHT, shading=True)
    lying = _mark("pencil", tilt=LYING_DOWN, shading=True)
    upright_h, upright_w = _thickness(upright), _extent(upright)[1]
    lying_h, lying_w = _thickness(lying), _extent(lying)[1]
    assert 2.2 * upright_h <= lying_h <= 3.3 * upright_h, f"altura {upright_h} → {lying_h}"
    assert abs(lying_w - upright_w) <= 4, f"largura {upright_w} → {lying_w}: a largura do grafite não muda"


def test_the_graphite_side_follows_the_azimuth():
    """Caneta pendendo para a direita: a marca se alonga na horizontal e a altura fica a do grafite."""
    upright = _mark("pencil", tilt=UPRIGHT, shading=True)
    lying = _mark("pencil", tilt=LYING_RIGHT, shading=True)
    upright_w, lying_w = _extent(upright)[1], _extent(lying)[1]
    assert lying_w >= upright_w + 40, f"largura {upright_w} → {lying_w}"
    assert abs(_thickness(lying) - _thickness(upright)) <= 4, f"altura {_thickness(upright)} → {_thickness(lying)}"


def test_the_stretch_grows_as_the_pen_lies_down():
    heights = [_thickness(_mark("pencil", tilt=(0.0, degrees), shading=True)) for degrees in (15.0, 35.0, 50.0, 70.0)]
    assert heights == sorted(heights) and heights[-1] > heights[0] + 30, heights


def test_the_graphite_side_deposits_less_per_area():
    """O lado do grafite espalha a mesma carga numa área maior: a marca é mais clara."""
    def mean_alpha(tilt):
        alpha = _mark("pencil", tilt=tilt, shading=True)
        return float(alpha[alpha > 5].mean())

    assert mean_alpha(LYING_DOWN) <= 0.9 * mean_alpha(UPRIGHT)


def test_the_switch_is_what_turns_the_graphite_side_on():
    assert np.array_equal(_mark("pencil", tilt=LYING_DOWN, shading=False), _mark("pencil", tilt=UPRIGHT, shading=False))
    assert not np.array_equal(_mark("pencil", tilt=LYING_DOWN, shading=True), _mark("pencil", tilt=LYING_DOWN, shading=False))


def test_the_switch_does_nothing_with_a_mouse_or_a_pen_standing_straight():
    assert np.array_equal(_mark("pencil", shading=True), _mark("pencil", shading=False))


def test_only_the_pencil_has_a_graphite_side():
    """O interruptor é do Lápis: ligado, não mexe em nenhum outro motor."""
    for name in ("inker", "marker", "oil"):
        assert np.array_equal(_mark(name, tilt=LYING_DOWN, shading=True), _mark(name, tilt=LYING_DOWN, shading=False)), name
