"""
test_out_of_bounds_content.py
=============================
Test suite for S10: Conteúdo fora da borda (Out-of-Bounds Content & Signed Tile Coordinates).
Validates that content placed, pasted, or transformed outside the canvas boundary
[0, width) x [0, height) is not discarded, and that signed tile coordinates work properly.
"""

from __future__ import annotations

import numpy as np
import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)


def _get_canvas_array(facade: native.PaintEngineFacade, w: int, h: int) -> np.ndarray:
    buf = facade.get_pixel_buffer()
    return np.frombuffer(buf, dtype=np.uint8).reshape((h, w, 4))


def test_paste_out_of_bounds_negative_coordinates():
    """Valida colar buffer parcialmente fora do canvas em coordenadas negativas.
    Os pixels dentro do canvas aparecem na tela, e os pixels fora do canvas
    são gravados nos tiles com coordenadas negativas."""
    w, h = 64, 64
    facade = native.PaintEngineFacade(w, h)
    facade.set_background_visibility(False)
    facade.add_layer("Layer1")
    facade.select_layer(0)

    # Cola um bloco 40x40 vermelho em (-20, -20)
    # A porção visível no canvas é (0, 0) a (20, 20)
    buf_size = 40 * 40
    red_buf = bytes([255, 0, 0, 255] * buf_size)
    assert facade.paste_rgba_buffer_on_active_layer(-20, -20, 40, 40, red_buf, 0, 1.0)

    arr = _get_canvas_array(facade, w, h)
    # Ponto (10, 10) está dentro do canvas e deve ser vermelho
    assert arr[10, 10, 0] == 255
    assert arr[10, 10, 3] == 255
    # Ponto (30, 30) está fora do bloco colado e deve ser transparente
    assert arr[30, 30, 3] == 0


def test_canvas_resize_preserves_out_of_bounds_content():
    """Valida que reduzir o tamanho do canvas não apaga o conteúdo fora da borda:
    ao re-expandir o canvas, o conteúdo externo reaparece intacto."""
    w, h = 128, 128
    facade = native.PaintEngineFacade(w, h)
    facade.set_background_visibility(False)
    facade.add_layer("Art")
    facade.select_layer(0)

    # Desenha na região (80, 80) a (120, 120) com verde
    buf = bytes([0, 255, 0, 255] * (40 * 40))
    assert facade.paste_rgba_buffer_on_active_layer(80, 80, 40, 40, buf, 0, 1.0)

    arr1 = _get_canvas_array(facade, w, h)
    assert arr1[100, 100, 1] == 255
    assert arr1[100, 100, 3] == 255

    # Encolhe o canvas para 64x64 (o ponto 100, 100 agora fica fora da borda)
    facade.resize_canvas(64, 64)
    arr2 = _get_canvas_array(facade, 64, 64)
    assert arr2.shape == (64, 64, 4)

    # Re-expande o canvas para 128x128
    facade.resize_canvas(128, 128)
    arr3 = _get_canvas_array(facade, 128, 128)
    # O conteúdo na posição (100, 100) deve estar preservado intacto!
    assert arr3[100, 100, 1] == 255
    assert arr3[100, 100, 3] == 255


def test_transform_commit_negative_translation():
    """Valida commit de transformação movendo conteúdo para fora do canvas."""
    w, h = 128, 128
    facade = native.PaintEngineFacade(w, h)
    facade.set_background_visibility(False)
    facade.add_layer("Layer1")
    facade.select_layer(0)

    # Cria retângulo azul de 40x40 em (20, 20)
    buf = bytes([0, 0, 255, 255] * (40 * 40))
    facade.paste_rgba_buffer_on_active_layer(20, 20, 40, 40, buf, 0, 1.0)

    # Inicia transformação
    assert facade.begin_transform()
    assert facade.is_transform_active()

    # Move -30 pixels para a esquerda (x passa de 20 para -10)
    # A porção visível no canvas passa a ser [0, 30)
    assert facade.commit_transform(
        -30.0, 0.0, 1.0, 1.0, 0.0, 40.0, 40.0, False, False, 0
    )
    assert not facade.is_transform_active()

    arr = _get_canvas_array(facade, w, h)
    # Ponto (10, 30) está no canvas e deve ser azul
    assert arr[30, 10, 2] == 255
    assert arr[30, 10, 3] == 255

    # Ponto (50, 30) agora está vazio
    assert arr[30, 50, 3] == 0


def test_paste_out_of_bounds_undo_redo():
    """Valida desfazer e refazer de colagem em coordenadas negativas."""
    w, h = 64, 64
    facade = native.PaintEngineFacade(w, h)
    facade.set_background_visibility(False)
    facade.add_layer("L1")
    facade.select_layer(0)

    buf = bytes([255, 255, 0, 255] * (30 * 30))
    facade.paste_rgba_buffer_on_active_layer(-10, 0, 30, 30, buf, 0, 1.0)

    arr = _get_canvas_array(facade, w, h)
    assert arr[10, 5, 0] == 255
    assert arr[10, 5, 1] == 255

    # Desfaz a colagem
    assert facade.undo()
    arr_undone = _get_canvas_array(facade, w, h)
    assert arr_undone[10, 5, 3] == 0

    # Refaz a colagem
    assert facade.redo()
    arr_redone = _get_canvas_array(facade, w, h)
    assert arr_redone[10, 5, 0] == 255
    assert arr_redone[10, 5, 1] == 255
