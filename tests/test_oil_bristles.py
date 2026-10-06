"""O Óleo é um feixe de cerdas que carrega tinta: riscos paralelos ao traço, tinta que acaba, cor que se mistura.

Até 2026-10-02 o Óleo era uma cor opaca com uma senoidal por cima. Medido numa pincelada reta de 240 px com
ranhuras em 100%:

  riscos        desvio do alfa no miolo 0,0 níveis (liso): a modulação era uma senoidal em coordenadas do
                carimbo, não do traço, e sumia sob dezenas de carimbos sobrepostos; no traço horizontal ela
                nem tinha como aparecer;
  brilho        o realce especular era somado de novo a cada carimbo, em cima do anterior, e só o do último
                carimbo sobrevivia (na prática, nenhum): nenhum pixel do miolo saía mais claro que a tinta;
  controles     `wet_mix_factor` e `paint_depletion` existiam no motor e nunca eram lidos; na ponte, nem
                existiam (o `.pyi` os declarava, o binário não).

Agora cada cerda lembra o que carrega (cor e carga), esgota ao longo do traço, pega cor da tela como ela
estava antes do traço e deixa riscos que seguem o movimento. O relevo é iluminado a partir do declive da
superfície, uma vez por pixel, sem acumular.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

W, H = 420, 420
CENTER = 210.0
INKS = [(30, 90, 170), (200, 60, 50), (240, 200, 60)]


def _engine():
    engine = native.PaintEngineFacade(W, H)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    engine.set_background_color(255, 255, 255, 255)
    return engine


def _oil(engine, color=INKS[0], size=40.0, spacing=0.06, impasto=0.0, grooves=0.0, specular=0.0, wet=0.0,
         depletion=0.0, flow=1.0, viscosity=0.7, hardness=0.8):
    engine.set_engine_type(int(native.EngineType.OilImpasto))
    profile = engine.get_brush_profile()
    profile.brush_size, profile.hardness, profile.opacity, profile.flow = size, hardness, 1.0, flow
    profile.spacing_factor = spacing
    profile.base_color = native.ColorRGBA(*color, 255)
    oil = profile.oil_params
    oil.impasto_depth, oil.bristle_grooves, oil.viscosity, oil.specular_brilliance = impasto, grooves, viscosity, specular
    oil.wet_mix_factor, oil.paint_depletion = wet, depletion
    return profile


def _stroke(engine, points, pressure=0.9):
    engine.begin_stroke_raw(points[0][0], points[0][1], pressure, 1.0)
    for i, (x, y) in enumerate(points[1:], 1):
        engine.update_stroke_raw(x, y, pressure, 1.0 + 8.0 * i)
    engine.end_stroke_raw()


def _path(angle_deg, length=240.0, count=150):
    a = math.radians(angle_deg)
    dx, dy = math.cos(a) * length / 2, math.sin(a) * length / 2
    return [(CENTER - dx + 2 * dx * i / (count - 1), CENTER - dy + 2 * dy * i / (count - 1)) for i in range(count)]


def _layer(engine):
    return np.frombuffer(bytes(engine.get_layer_pixel_buffer(0)), dtype=np.uint8).reshape(H, W, 4).astype(int)


def _core_mask(angle_deg, length=240.0, size=40.0):
    """Os pixels do miolo de uma pincelada reta que atravessa o centro com esse ângulo."""
    a = math.radians(angle_deg)
    ys, xs = np.mgrid[0:H, 0:W]
    dx, dy = xs + 0.5 - CENTER, ys + 0.5 - CENTER
    along = dx * math.cos(a) + dy * math.sin(a)
    across = -dx * math.sin(a) + dy * math.cos(a)
    return (np.abs(along) < length * 0.3) & (np.abs(across) < size * 0.32)


def _correlation(alpha, mask, vx, vy):
    sx, sy = int(round(vx)), int(round(vy))
    shifted = np.roll(np.roll(alpha, -sy, axis=0), -sx, axis=1)
    both = mask & np.roll(np.roll(mask, -sy, axis=0), -sx, axis=1)
    first, second = alpha[both], shifted[both]
    if first.std() < 1e-6 or second.std() < 1e-6:
        return float("nan")
    return float(np.corrcoef(first, second)[0, 1])


def _streaks(angle, spacing=0.06):
    """(correlação ao longo do traço, correlação através dele, desvio do alfa) no miolo de uma pincelada."""
    engine = _engine()
    _oil(engine, grooves=1.0, spacing=spacing)
    _stroke(engine, _path(angle))
    alpha = _layer(engine)[:, :, 3].astype(float)
    mask = _core_mask(angle)
    a = math.radians(angle)
    return (_correlation(alpha, mask, 4 * math.cos(a), 4 * math.sin(a)),
            _correlation(alpha, mask, -4 * math.sin(a), 4 * math.cos(a)),
            float(alpha[mask].std()))


# ── 1. A cor da tinta ───────────────────────────────────────────────────────

@pytest.mark.parametrize("ink", INKS)
@pytest.mark.parametrize("spacing", [0.04, 0.2])
@pytest.mark.parametrize("wet", [0.0, 1.0])
def test_a_plain_stroke_on_an_empty_layer_has_exactly_the_chosen_color(ink, spacing, wet):
    """Sem relevo, a cor do miolo é a cor escolhida, e misturar com uma tela vazia não suja a cerda."""
    engine = _engine()
    _oil(engine, color=ink, spacing=spacing, wet=wet)
    _stroke(engine, _path(0))
    pixels = _layer(engine)
    core = pixels[_core_mask(0)]
    assert core[:, 3].min() == 255
    error = np.abs(core[:, :3] - np.array(ink)).max()
    assert error <= 1, f"o miolo saiu {tuple(core[:, :3].mean(axis=0).round())} em vez de {ink}"


# ── 2. Os riscos seguem o traço ─────────────────────────────────────────────

@pytest.mark.parametrize("angle", [0, 90, 45, 135])
def test_the_grooves_run_along_the_stroke_in_every_direction(angle):
    along, across, deviation = _streaks(angle)
    assert deviation >= 12, f"{angle}°: o alfa do miolo quase não varia ({deviation:.1f} níveis): sem riscos"
    assert along >= 0.8, f"{angle}°: pixels vizinhos ao longo do traço deveriam se parecer (correlação {along:.2f})"
    assert across <= 0.5, f"{angle}°: pixels vizinhos através do traço não deveriam se parecer ({across:.2f})"


def test_without_grooves_the_stroke_is_flat():
    engine = _engine()
    _oil(engine, grooves=0.0)
    _stroke(engine, _path(0))
    assert _layer(engine)[:, :, 3][_core_mask(0)].std() == 0


def test_the_streaks_do_not_depend_on_the_spacing():
    """O contraste dos riscos fica o mesmo com 4 ou com 20% de espaçamento: o teto de cobertura é por cerda."""
    close, normal, wide = (_streaks(0, spacing)[2] for spacing in (0.04, 0.08, 0.2))
    assert abs(close - normal) <= 0.15 * normal, f"{close:.1f} contra {normal:.1f}"
    assert abs(wide - normal) <= 0.25 * normal, f"{wide:.1f} contra {normal:.1f}"


# ── 3. A tinta acaba ────────────────────────────────────────────────────────

def _thirds(depletion, spacing=0.06):
    engine = _engine()
    _oil(engine, size=30.0, grooves=0.5, depletion=depletion, spacing=spacing)
    _stroke(engine, [(20.0 + 380.0 * i / 159, 210.0) for i in range(160)])
    band = _layer(engine)[200:221, :, 3].astype(float)
    return [band[:, a:b].mean() for a, b in ((30, 130), (150, 250), (290, 390))]


def test_the_brush_runs_dry_along_the_stroke():
    """Último terço sobre o primeiro (traço de 8 diâmetros): 0,99 / 0,80 / 0,26 / 0,01 para 0 / 25 / 50 / 100%."""
    ratios = {d: _thirds(d)[2] / _thirds(d)[0] for d in (0.0, 0.25, 0.5, 1.0)}
    assert ratios[0.0] >= 0.95, f"sem esgotamento a tinta não deveria acabar ({ratios[0.0]:.2f})"
    assert ratios[0.25] < ratios[0.0] - 0.1
    assert ratios[0.5] <= 0.5
    assert ratios[1.0] <= 0.1
    assert ratios[0.0] > ratios[0.25] > ratios[0.5] > ratios[1.0]


def test_the_depletion_length_does_not_depend_on_the_spacing():
    close, wide = (_thirds(0.5, spacing)[2] / _thirds(0.5, spacing)[0] for spacing in (0.04, 0.2))
    assert abs(close - wide) <= 0.03, f"espaçamento 0,04 -> {close:.2f}, 0,2 -> {wide:.2f}"


# ── 4. A cor se mistura ─────────────────────────────────────────────────────

def _after_a_blue_block(wet):
    """Vermelho passando por um bloco azul: a cor do traço logo depois do bloco."""
    engine = _engine()
    engine.set_engine_type(int(native.EngineType.Brush))
    profile = engine.get_brush_profile()
    profile.brush_size, profile.hardness, profile.opacity, profile.flow = 60.0, 1.0, 1.0, 1.0
    profile.base_color = native.ColorRGBA(30, 90, 190, 255)
    _stroke(engine, [(150.0, 150.0 + 6 * i) for i in range(21)])
    _oil(engine, color=(200, 40, 40), wet=wet)
    _stroke(engine, [(40.0 + 340.0 * i / 159, 210.0) for i in range(160)])
    return _layer(engine)[205:216, 200:260, :3].reshape(-1, 3).mean(axis=0)


def test_the_wet_mix_drags_the_color_of_the_canvas_into_the_stroke():
    """Logo depois do bloco azul o azul do traço sobe de 40 para 40 / 45 / 58 / 87 com 0 / 35 / 70 / 100%."""
    blues = [_after_a_blue_block(wet)[2] for wet in (0.0, 0.35, 0.7, 1.0)]
    assert blues[0] <= 41, "sem mistura o traço deveria continuar vermelho puro"
    assert blues[3] >= blues[0] + 30, f"o azul não foi arrastado ({blues})"
    assert blues[0] < blues[1] < blues[2] < blues[3]


def test_the_mixed_stroke_goes_back_to_the_pure_color_far_from_the_block():
    """A reserva repõe a tinta: 200 px depois do bloco o vermelho já voltou perto do puro."""
    engine = _engine()
    engine.set_engine_type(int(native.EngineType.Brush))
    profile = engine.get_brush_profile()
    profile.brush_size, profile.hardness, profile.opacity, profile.flow = 60.0, 1.0, 1.0, 1.0
    profile.base_color = native.ColorRGBA(30, 90, 190, 255)
    _stroke(engine, [(100.0, 150.0 + 6 * i) for i in range(21)])
    _oil(engine, color=(200, 40, 40), wet=1.0)
    _stroke(engine, [(30.0 + 380.0 * i / 159, 210.0) for i in range(160)])
    far = _layer(engine)[205:216, 340:400, :3].reshape(-1, 3).mean(axis=0)
    assert abs(far[0] - 200) <= 8 and far[2] <= 55, f"{far.round()}"


# ── 5. O relevo ─────────────────────────────────────────────────────────────

def _lit_core(spacing, impasto=1.0, specular=1.0):
    engine = _engine()
    _oil(engine, grooves=1.0, impasto=impasto, specular=specular, spacing=spacing)
    _stroke(engine, _path(0))
    core = _layer(engine)[198:222, 120:300].reshape(-1, 4)
    return core[core[:, 3] >= 250][:, :3]


def test_the_relief_lights_the_ridges_without_accumulating():
    """A média do miolo iluminado é a mesma com 4 ou com 8% de espaçamento (56,0 / 56,4 de vermelho)."""
    close, normal = _lit_core(0.04), _lit_core(0.08)
    assert close.std(axis=0).min() >= 8, "o relevo quase não aparece"
    assert np.abs(close.mean(axis=0) - normal.mean(axis=0)).max() <= 3


def test_without_impasto_and_specular_the_grooves_do_not_tint_the_core():
    solid = _lit_core(0.06, impasto=0.0, specular=0.0)
    assert np.abs(solid - np.array(INKS[0])).max() <= 1


def test_the_light_never_burns_a_channel():
    solid = _lit_core(0.06)
    assert solid.max() <= 255 and solid.min() >= 0
    assert (solid == 255).mean() < 0.02


# ── 6. Um traço novo começa limpo ───────────────────────────────────────────

def test_each_stroke_starts_with_clean_bristles():
    """Desfazer e repetir o mesmo traço dá os mesmos bytes: nada das cerdas do primeiro vaza para o segundo."""
    engine = _engine()
    _oil(engine, grooves=0.8, wet=0.8, depletion=0.3, impasto=0.6, specular=0.5)
    _stroke(engine, _path(30))
    first = bytes(engine.get_layer_pixel_buffer(0))
    assert engine.undo()
    _stroke(engine, _path(30))
    assert bytes(engine.get_layer_pixel_buffer(0)) == first


def test_a_stroke_does_not_depend_on_what_the_engine_painted_before():
    fresh, used = _engine(), _engine()
    for engine in (fresh, used):
        _oil(engine, grooves=0.8, wet=0.8, depletion=0.3, impasto=0.6, specular=0.5)
    _stroke(used, _path(120, length=160))
    assert used.undo()
    for engine in (fresh, used):
        _stroke(engine, _path(30))
    assert bytes(fresh.get_layer_pixel_buffer(0)) == bytes(used.get_layer_pixel_buffer(0))


# ── 7. Trava de alfa, seleção, desfazer e o contrato ────────────────────────

def test_alpha_lock_paints_the_color_and_keeps_the_alpha():
    engine = _engine()
    engine.set_engine_type(int(native.EngineType.Brush))
    profile = engine.get_brush_profile()
    profile.brush_size, profile.hardness, profile.opacity, profile.flow = 60.0, 1.0, 1.0, 1.0
    profile.base_color = native.ColorRGBA(240, 240, 240, 255)
    _stroke(engine, _path(0, length=300))
    engine.set_layer_alpha_lock(0, True)
    before = _layer(engine)
    _oil(engine, grooves=0.6, impasto=0.5, specular=0.4)
    _stroke(engine, _path(0))
    after = _layer(engine)
    assert np.array_equal(after[:, :, 3], before[:, :, 3]), "a trava de alfa mudou o alfa"
    assert np.abs(after[:, :, :3] - before[:, :, :3]).max() > 40, "o óleo não pintou o pixel travado"


def test_selection_limits_the_stroke():
    engine = _engine()
    assert engine.select_rect(0, 0, 200, H, mode=0)
    _oil(engine, grooves=0.5, impasto=0.5, specular=0.5)
    _stroke(engine, _path(0, length=300))
    alpha = _layer(engine)[:, :, 3]
    assert alpha[:, :198].max() > 0 and alpha[:, 203:].max() == 0


def test_undo_removes_the_whole_stroke_and_redo_brings_it_back():
    engine = _engine()
    _oil(engine, grooves=0.8, impasto=0.6, specular=0.5, wet=0.5)
    _stroke(engine, _path(45))
    painted = bytes(engine.get_layer_pixel_buffer(0))
    assert engine.undo()
    assert int((_layer(engine)[:, :, 3] > 0).sum()) == 0, "o desfazer deixou tinta para trás"
    assert engine.redo() and bytes(engine.get_layer_pixel_buffer(0)) == painted


def test_the_two_controls_are_part_of_the_bridge_contract():
    """O `.pyi` declarava `wet_mix_factor` e `paint_depletion`; o binário não os tinha."""
    oil = native.BrushProfile().oil_params
    assert oil.wet_mix_factor == pytest.approx(0.5) and oil.paint_depletion == pytest.approx(0.0)
    oil.wet_mix_factor, oil.paint_depletion = 0.25, 0.75
    assert (oil.wet_mix_factor, oil.paint_depletion) == (pytest.approx(0.25), pytest.approx(0.75))
