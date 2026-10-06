"""O Borrar arrasta um pedaço da imagem: não deriva a cor, não cria tinta e o arrasto não depende do espaçamento.

Até 2026-10-02 o Borrar carregava UMA cor (a média gaussiana do dab) e a pintava, opaca, sobre tudo o que
pisava. Medido numa camada de (200, 100, 50) liso, seis passadas do preset 'Esfuminho Suave':

  cor do miolo     (175, 78, 32) em vez de (200, 100, 50): 32 níveis de deriva, porque cada passada
                   misturava bytes retos e a cor carregada nunca era a do chão;
  linha fina       uma linha preta de 3 px sobre branco virava uma faixa cinza: a tinta DEPOIS do traço
                   era 469% da de antes (o motor criava tinta), e a linha sumia sob a cor média;
  comprimento      o fim do arrasto ia de x=84 a x=190 só por mudar o espaçamento de 0,2 para 0,04.

Agora o pincel carrega um pedaço da imagem, em alfa pré-multiplicado e ponto flutuante (`SmearPatch`):
área lisa arrastada continua igual, a tinta se move em vez de nascer, e a força é por distância.
"""

from __future__ import annotations

import numpy as np
import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

W, H = 260, 90


def _engine():
    engine = native.PaintEngineFacade(W, H)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    engine.set_background_color(255, 255, 255, 255)
    return engine


def _stroke(engine, points, pressure=0.9):
    engine.begin_stroke_raw(points[0][0], points[0][1], pressure, 1.0)
    for i, (x, y) in enumerate(points[1:], 1):
        engine.update_stroke_raw(x, y, pressure, 1.0 + 8.0 * i)
    engine.end_stroke_raw()


def _paint(engine, color, size, points, hardness=1.0):
    engine.set_engine_type(int(native.EngineType.Brush))
    profile = engine.get_brush_profile()
    profile.brush_size, profile.hardness, profile.opacity, profile.flow = size, hardness, 1.0, 1.0
    profile.base_color = native.ColorRGBA(*color, 255)
    _stroke(engine, points)


def _smudge(engine, points, size=24.0, pickup=0.7, mix=0.5, stretch=0.8, flow=0.7, spacing=0.08, hardness=0.5):
    engine.set_engine_type(int(native.EngineType.Smudge))
    profile = engine.get_brush_profile()
    profile.brush_size, profile.hardness, profile.opacity, profile.spacing_factor = size, hardness, 1.0, spacing
    profile.flow = flow
    profile.smudge_params.color_pickup = pickup
    profile.smudge_params.mix_ratio = mix
    profile.smudge_params.smudge_stretch = stretch
    _stroke(engine, points)


def _layer(engine):
    return np.frombuffer(bytes(engine.get_layer_pixel_buffer(0)), dtype=np.uint8).reshape(H, W, 4).astype(int)


def _shown(engine):
    return np.frombuffer(bytes(engine.get_pixel_buffer()), dtype=np.uint8).reshape(H, W, 4).astype(int)


def _white_page_with_line():
    engine = _engine()
    _paint(engine, (255, 255, 255), 80, [(0.0, 45.0), (260.0, 45.0)])
    _paint(engine, (0, 0, 0), 3, [(100.0, 10.0), (100.0, 80.0)])
    return engine


# ── 1. Área lisa é ponto fixo ───────────────────────────────────────────────

def test_dragging_across_a_flat_color_changes_nothing():
    """Seis passadas por cima de (200, 100, 50) liso: a cor continua exatamente a mesma."""
    engine = _engine()
    _paint(engine, (200, 100, 50), 80, [(10.0, 45.0), (250.0, 45.0)])
    before = _layer(engine)
    for k in range(6):
        _smudge(engine, [(30.0 + k, 40.0 + k), (230.0, 45.0)])
    drift = np.abs(_layer(engine) - before)[30:60, 40:220].max()
    assert drift == 0, f"a cor derivou {drift} níveis em seis passadas"


def test_a_tap_without_movement_changes_nothing():
    engine = _white_page_with_line()
    before = bytes(engine.get_layer_pixel_buffer(0))
    _smudge(engine, [(100.0, 45.0), (100.0, 45.0)])
    assert bytes(engine.get_layer_pixel_buffer(0)) == before


# ── 2. A tinta se move; não nasce ───────────────────────────────────────────

def test_smearing_a_thin_line_does_not_create_ink():
    """Uma linha preta de 3 px arrastada por cima: a tinta total não passa da que havia (antes: 469%)."""
    engine = _white_page_with_line()
    before = (255 - _shown(engine)[:, :, :3].mean(axis=2))[35:56].sum()
    _smudge(engine, [(60.0, 45.0), (200.0, 45.0)])
    after = (255 - _shown(engine)[:, :, :3].mean(axis=2))[35:56].sum()
    assert before > 0
    assert after <= before * 1.05, f"o arrasto criou tinta: {after / before:.0%} da original"
    assert after >= before * 0.4, f"a linha desapareceu em vez de ser arrastada: {after / before:.0%} sobra"


def test_the_color_of_one_side_is_dragged_into_the_other():
    """Vermelho à esquerda, azul à direita: arrastar para a direita puxa vermelho para dentro do azul."""
    engine = _engine()
    _paint(engine, (200, 40, 40), 80, [(0.0, 45.0), (128.0, 45.0)])
    _paint(engine, (40, 40, 200), 80, [(129.0, 45.0), (260.0, 45.0)])
    blue_red_channel = _layer(engine)[45, 150, 0]
    _smudge(engine, [(70.0, 45.0), (200.0, 45.0)], mix=0.8, flow=0.9)
    dragged = _layer(engine)[45, 150, 0]
    assert dragged >= blue_red_channel + 25, f"o vermelho não foi arrastado ({blue_red_channel} -> {dragged})"
    assert _layer(engine)[45, 60, 0] >= 150, "a origem do arrasto deveria continuar vermelha"


# ── 3. O comprimento do arrasto não depende do espaçamento ──────────────────

def _drag_length(spacing):
    engine = _engine()
    _paint(engine, (20, 40, 160), 30, [(30.0, 45.0), (40.0, 45.0)])
    _smudge(engine, [(30.0, 45.0), (250.0, 45.0)], spacing=spacing)
    alpha = _layer(engine)[45, :, 3].astype(float)
    reference = alpha[48:52].mean()
    below = np.where(alpha[50:] < reference / np.e)[0]
    return int(below.min() + 50) if below.size else W


def test_the_drag_length_does_not_change_with_the_spacing():
    close, normal = _drag_length(0.04), _drag_length(0.08)
    assert abs(close - normal) <= 0.1 * normal, f"espaçamento 0,04 -> {close}, 0,08 -> {normal}"
    assert abs(_drag_length(0.2) - normal) <= 0.25 * normal


# ── 4. Trava de alfa, seleção e desfazer ────────────────────────────────────

def test_alpha_lock_moves_the_color_and_keeps_the_alpha():
    engine = _engine()
    _paint(engine, (200, 40, 40), 30, [(30.0, 45.0), (120.0, 45.0)])
    _paint(engine, (40, 40, 200), 30, [(120.0, 45.0), (220.0, 45.0)])
    engine.set_layer_alpha_lock(0, True)
    before = _layer(engine)
    _smudge(engine, [(50.0, 45.0), (210.0, 45.0)], mix=0.8, flow=0.9)
    got = _layer(engine)
    assert np.array_equal(got[:, :, 3], before[:, :, 3]), "a trava de alfa mudou o alfa"
    assert np.abs(got[:, :, :3] - before[:, :, :3]).max() > 10, "a cor não foi arrastada"


def test_selection_limits_the_smear():
    engine = _white_page_with_line()
    assert engine.select_rect(0, 0, 100, H, mode=0)
    before = _layer(engine)
    _smudge(engine, [(60.0, 45.0), (200.0, 45.0)])
    after = _layer(engine)
    assert np.array_equal(after[:, 102:], before[:, 102:]), "o arrasto passou da seleção"
    assert np.abs(after[:, :100] - before[:, :100]).max() > 0


def test_undo_restores_the_layer_exactly():
    engine = _white_page_with_line()
    before = bytes(engine.get_layer_pixel_buffer(0))
    _smudge(engine, [(60.0, 45.0), (200.0, 45.0)])
    assert bytes(engine.get_layer_pixel_buffer(0)) != before
    assert engine.undo() and bytes(engine.get_layer_pixel_buffer(0)) == before
