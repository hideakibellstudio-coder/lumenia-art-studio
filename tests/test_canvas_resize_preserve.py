"""Redimensionar o canvas preserva cada pixel das camadas, e a composição não desfaz a compressão (S1).

A fundação do compositor foi medida em 2026-10-02 (docs/05-visao-e-futuro/03): redimensionar +256 px num
canvas de 4096² com 10 camadas custava 1,5 s, porque a grade de tiles era refeita pixel a pixel com uma busca
por pixel; e `compress_inactive_layers` encolhia os tiles de 181 para 126 MB só até a primeira composição,
que descomprimia tudo de vez. A troca (cópia por tile, leitura de composição sem descomprimir) não pode mudar
um pixel, então o oráculo daqui não depende dela: um recorte/translação feito em numpy sobre o que o próprio
motor devolve antes de redimensionar, com pixels de alfa 0 que ainda têm cor (o que a borracha deixa), tiles
compartilhados por cópia-na-escrita (camada duplicada) e tiles comprimidos.
"""

from __future__ import annotations

import numpy as np
import pytest

native = pytest.importorskip("aladyn_engine_native", reason="módulo nativo não compilado neste ambiente")

BACKGROUND = (255, 255, 255, 255)


def _stroke(engine, kind, size, hardness, color, x0, y0, steps=24, dx=9.0):
    engine.set_engine_type(int(kind))
    profile = engine.get_brush_profile()
    profile.brush_size, profile.hardness, profile.opacity, profile.flow = size, hardness, 1.0, 1.0
    profile.base_color = native.ColorRGBA(*color, 255)
    engine.begin_stroke_raw(x0, y0, 1.0, 1.0)
    for i in range(1, steps + 1):
        engine.update_stroke_raw(x0 + i * dx, y0 + (i % 4) * 3.0, 1.0, 1.0 + i * 0.008)
    engine.end_stroke_raw()


def _scene(width, height, seed=5):
    """Três camadas: pasta opaca e translúcida, traço macio apagado pela borracha (alfa 0 com cor) e uma cópia."""
    engine = native.PaintEngineFacade(width, height)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    rng = np.random.default_rng(seed)

    bottom = engine.add_layer("blocks")
    engine.select_layer(bottom)
    for _ in range(6):
        w, h = int(rng.integers(20, width // 2)), int(rng.integers(20, height // 2))
        block = rng.integers(0, 256, (h, w, 4), dtype=np.uint8)
        block[..., 3] = rng.choice((90, 200, 255), size=(h, w))
        engine.paste_rgba_buffer_on_active_layer(
            int(rng.integers(0, width - w)), int(rng.integers(0, height - h)), w, h, block.tobytes(), 0, 1.0)

    middle = engine.add_layer("erased")
    engine.select_layer(middle)
    run = (width - 40) // 8  # passos de 8 px: o traço e a borracha passam pelos mesmos pontos
    _stroke(engine, native.EngineType.Brush, 42.0, 0.0, (200, 40, 40), 10.0, height / 2, steps=run, dx=8.0)
    _stroke(engine, native.EngineType.Eraser, 42.0, 0.0, (0, 0, 0), 10.0, height / 2, steps=run, dx=8.0)

    copy = engine.duplicate_layer(bottom)  # os tiles passam a ser compartilhados por cópia-na-escrita
    if copy <= middle:
        middle += 1  # a cópia entra logo acima da original e empurra as camadas de cima
    engine.select_layer(copy)
    _stroke(engine, native.EngineType.Brush, 30.0, 0.8, (30, 90, 200), width / 3, height / 4, steps=8, dx=7.0)
    return engine, (bottom, middle, copy)


def _layer(engine, index):
    width, height = engine.get_width(), engine.get_height()
    return np.frombuffer(bytes(engine.get_layer_pixel_buffer(index)), dtype=np.uint8).reshape(height, width, 4).copy()


def _screen(engine):
    width, height = engine.get_width(), engine.get_height()
    return np.frombuffer(bytes(engine.get_display_region(0, 0, width, height)), dtype=np.uint8).reshape(height, width, 4).copy()


def _cropped(pixels, width, height):
    out = np.zeros((height, width, 4), dtype=np.uint8)
    h, w = min(height, pixels.shape[0]), min(width, pixels.shape[1])
    out[:h, :w] = pixels[:h, :w]
    return out


# Grandes e pequenos, com a borda de tile (128) caindo no meio do canvas, de um lado e do outro.
RESIZES = [
    ((300, 200), (520, 390)),   # cresce nos dois eixos, atravessando a borda do último tile
    ((700, 500), (333, 129)),   # encolhe cortando tiles ao meio
    ((300, 300), (500, 100)),   # cresce numa direção e encolhe na outra
    ((256, 256), (257, 257)),   # um pixel a mais: o tile novo quase vazio
    ((384, 256), (128, 128)),   # encolhe até um tile exato
    ((300, 200), (300, 200)),   # mesmo tamanho
]


@pytest.mark.parametrize("before,after", RESIZES)
def test_every_pixel_of_every_layer_survives_a_resize_exactly(before, after):
    engine, layers = _scene(*before)
    assert any(((_layer(engine, i)[..., 3] == 0) & (_layer(engine, i)[..., :3].max(axis=2) > 0)).any() for i in layers), \
        "a cena precisa ter pixels de alfa 0 com cor (o que a borracha deixa), senão o teste não os cobre"
    expected = {i: _cropped(_layer(engine, i), *after) for i in layers}
    engine.resize_canvas(*after)
    assert (engine.get_width(), engine.get_height()) == after
    for index in layers:
        assert np.array_equal(_layer(engine, index), expected[index]), f"camada {index}: {before} -> {after}"


@pytest.mark.parametrize("before,after", RESIZES)
def test_the_screen_after_a_resize_is_the_old_screen_where_they_overlap_and_the_background_elsewhere(before, after):
    """Um pixel composto só depende dos pixels das camadas nele e do fundo: a parte comum não pode mudar."""
    engine, _ = _scene(*before)
    old = _screen(engine)
    engine.resize_canvas(*after)
    new = _screen(engine)
    assert new.shape[:2] == (after[1], after[0])
    h, w = min(before[1], after[1]), min(before[0], after[0])
    assert np.array_equal(new[:h, :w], old[:h, :w])
    outside = np.ones(new.shape[:2], dtype=bool)
    outside[:h, :w] = False
    assert (new[outside] == np.array(BACKGROUND, dtype=np.uint8)).all()


def test_a_resize_with_compressed_layers_changes_nothing():
    """Camadas comprimidas (inativas, depois de `compress_inactive_layers`) são redimensionadas como as demais."""
    engine, layers = _scene(300, 200)
    engine.select_layer(layers[-1])
    expected = {i: _cropped(_layer(engine, i), 410, 150) for i in layers}
    engine.compress_inactive_layers()
    engine.resize_canvas(410, 150)
    for index in layers:
        assert np.array_equal(_layer(engine, index), expected[index]), f"camada {index}"


def test_what_a_shrink_cuts_stays_cut_when_the_canvas_grows_back():
    """Tiles de borda cortados ao meio: a parte de fora some de verdade, não só da leitura."""
    engine, layers = _scene(300, 200)
    before = {i: _layer(engine, i) for i in layers}
    engine.resize_canvas(133, 71)
    engine.resize_canvas(300, 200)
    for index in layers:
        back = _layer(engine, index)
        assert np.array_equal(back[:71, :133], before[index][:71, :133]), f"camada {index}: parte que ficou"
        assert not back[71:].any() and not back[:, 133:].any(), f"camada {index}: parte cortada voltou"


def test_painting_after_a_resize_works_and_never_leaks_into_a_layer_that_shared_tiles():
    """Depois de redimensionar, pintar na área nova funciona e não mexe nas camadas duplicadas (cópia-na-escrita)."""
    engine, (bottom, middle, copy) = _scene(300, 200)
    engine.resize_canvas(520, 390)
    copy_before = _layer(engine, copy)
    bottom_before = _layer(engine, bottom)
    engine.select_layer(bottom)
    _stroke(engine, native.EngineType.Brush, 40.0, 0.9, (10, 160, 60), 330.0, 300.0, steps=10, dx=12.0)
    painted = _layer(engine, bottom)
    assert painted[250:350, 330:440].any(), "o traço na área nova deveria aparecer"
    assert np.array_equal(_layer(engine, copy), copy_before), "a camada duplicada não pode mudar com o traço da outra"
    assert not np.array_equal(painted, bottom_before)


def test_composition_does_not_undo_the_compression_of_inactive_layers():
    """Medido em 2026-10-02 (4096², 10 camadas): 126 MB comprimido, 181 MB depois de qualquer composição.

    A composição lê os tiles; ler não pode descomprimi-los de vez. Cores chapadas comprimem bem, então o
    número fica longe do ruído da medida."""
    width = height = 1024
    engine = native.PaintEngineFacade(width, height)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    rng = np.random.default_rng(2)
    indexes = []
    for i in range(6):
        index = engine.add_layer(f"flat{i}")
        engine.select_layer(index)
        block = np.empty((700, 700, 4), dtype=np.uint8)
        block[:] = (int(rng.integers(0, 256)), 60, 120, 200)
        engine.paste_rgba_buffer_on_active_layer(int(rng.integers(0, 324)), int(rng.integers(0, 324)), 700, 700, block.tobytes(), 0, 1.0)
        indexes.append(index)
    engine.select_layer(indexes[-1])
    plain = _screen(engine)

    full = engine.get_total_tile_memory_mb()
    engine.compress_inactive_layers()
    compressed = engine.get_total_tile_memory_mb()
    assert compressed < 0.5 * full, "o conteúdo chapado deveria comprimir bem (senão o teste não prova nada)"

    engine.set_layer_opacity(indexes[0], 0.99)        # recompõe a região da camada
    engine.set_layer_opacity(indexes[0], 1.0)
    engine.add_layer("recompose-everything")           # estrutural: recompõe o canvas inteiro
    after = engine.get_total_tile_memory_mb()
    assert after <= compressed * 1.05 + 0.1, (full, compressed, after)
    assert np.array_equal(_screen(engine), plain), "a imagem não pode mudar por causa da compressão"
