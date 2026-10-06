"""
test_layer_mask.py
==================
Test suite for S9: Layer Masks (Máscaras de Camada).
Validates mask creation, querying, toggling, target editing,
numerical compositing math (srcA * maskA), 16-bit support, and undo/redo.
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


def _fill_rect(facade: native.PaintEngineFacade, x: int, y: int, w: int, h: int, color: native.ColorRGBA):
    buf = bytes([color.r, color.g, color.b, color.a] * (w * h))
    facade.paste_rgba_buffer_on_active_layer(x, y, w, h, buf, 0, 1.0)


def test_mask_lifecycle_creation_and_removal():
    w, h = 64, 64
    facade = native.PaintEngineFacade(w, h)
    idx = facade.add_layer("Camada 1")
    assert idx >= 0

    assert not facade.has_layer_mask(idx)
    assert not facade.is_layer_mask_enabled(idx)
    assert not facade.is_layer_mask_edit_target(idx)

    # Adicionar máscara
    assert facade.add_layer_mask(idx)
    assert facade.has_layer_mask(idx)
    assert facade.is_layer_mask_enabled(idx)

    # Não pode adicionar máscara duas vezes na mesma camada
    assert not facade.add_layer_mask(idx)

    # Desabilitar e reabilitar
    facade.set_layer_mask_enabled(idx, False)
    assert not facade.is_layer_mask_enabled(idx)
    facade.set_layer_mask_enabled(idx, True)
    assert facade.is_layer_mask_enabled(idx)

    # Definir alvo de edição da máscara
    facade.set_layer_mask_edit_target(idx, True)
    assert facade.is_layer_mask_edit_target(idx)
    facade.set_layer_mask_edit_target(idx, False)
    assert not facade.is_layer_mask_edit_target(idx)

    # Remover máscara
    assert facade.remove_layer_mask(idx)
    assert not facade.has_layer_mask(idx)
    assert not facade.remove_layer_mask(idx)


def test_mask_cannot_be_added_to_group_or_filter():
    facade = native.PaintEngineFacade(64, 64)
    grp_idx = facade.add_group("Grupo")
    assert not facade.add_layer_mask(grp_idx)


def test_mask_raster_compositing_math():
    """Valida a matemática do compositor com máscara:
    Preenche a camada de vermelho.
    Pinta metade da máscara de preto (oculta) e um quarto de cinza 50%."""
    w, h = 100, 100
    facade = native.PaintEngineFacade(w, h)
    facade.set_background_visibility(False)

    # Camada 0: Vermelho opaco (255, 0, 0, 255) cobrindo (20, 20) a (80, 80)
    facade.add_layer("Desenho")
    facade.select_layer(0)
    _fill_rect(facade, 20, 20, 60, 60, native.ColorRGBA(255, 0, 0, 255))

    arr_before = _get_canvas_array(facade, w, h)
    assert arr_before[50, 50, 0] == 255
    assert arr_before[50, 50, 3] == 255

    # Adiciona máscara
    assert facade.add_layer_mask(0)

    # Antes de pintar na máscara, ela revela tudo por padrão
    arr_unpainted = _get_canvas_array(facade, w, h)
    assert arr_unpainted[50, 50, 0] == 255
    assert arr_unpainted[50, 50, 3] == 255

    # Alvo de edição passa para a máscara
    facade.set_layer_mask_edit_target(0, True)
    assert facade.is_layer_mask_edit_target(0)

    # Pinta retângulo preto (0, 0, 0, 255) no quadrante esquerdo (20, 20, 30, 60)
    _fill_rect(facade, 20, 20, 30, 60, native.ColorRGBA(0, 0, 0, 255))

    arr_masked = _get_canvas_array(facade, w, h)

    # Quadrante esquerdo (30, 50): Deve estar totalmente mascarado / transparente (Alpha=0)
    assert arr_masked[50, 30, 3] == 0, f"Pixel mascarado com preto deve ter Alpha=0, obtido {arr_masked[50, 30, 3]}"

    # Quadrante direito (60, 50): Não foi tocado na máscara, permanece vermelho opaco
    assert arr_masked[50, 60, 0] == 255
    assert arr_masked[50, 60, 3] == 255

    # Agora pinta uma área com cinza 128 (50% de transparência) em (55, 20, 25, 30)
    _fill_rect(facade, 55, 20, 25, 30, native.ColorRGBA(128, 128, 128, 255))

    arr_gray = _get_canvas_array(facade, w, h)
    # Ponto (60, 30) deve ter opacidade aproximada de 50% (~128)
    gray_alpha = int(arr_gray[30, 60, 3])
    assert 120 <= gray_alpha <= 136, f"Pixel com cinza na máscara deve ter Alpha ~128, obtido {gray_alpha}"

    # Desativa a máscara temporariamente
    facade.set_layer_mask_enabled(0, False)
    arr_disabled = _get_canvas_array(facade, w, h)
    # A área que estava mascarada deve voltar a aparecer totalmente opaca
    assert arr_disabled[50, 30, 0] == 255
    assert arr_disabled[50, 30, 3] == 255

    # Reativa a máscara
    facade.set_layer_mask_enabled(0, True)
    arr_reenabled = _get_canvas_array(facade, w, h)
    assert arr_reenabled[50, 30, 3] == 0


def test_mask_in_rgba16_document():
    """Valida máscara de camada em documento de 16 bits (PixelFormat::RGBA16)."""
    w, h = 64, 64
    facade = native.PaintEngineFacade(w, h, 1)  # 1 = RGBA16
    assert facade.get_pixel_format() == 1
    facade.set_background_visibility(False)

    facade.add_layer("Layer16")
    facade.select_layer(0)
    _fill_rect(facade, 10, 10, 40, 40, native.ColorRGBA(0, 255, 0, 255))

    assert facade.add_layer_mask(0)
    facade.set_layer_mask_edit_target(0, True)

    # Mascara metade com preto
    _fill_rect(facade, 10, 10, 20, 40, native.ColorRGBA(0, 0, 0, 255))

    arr = _get_canvas_array(facade, w, h)
    # Área mascarada (15, 20) tem alpha 0
    assert arr[20, 15, 3] == 0
    # Área visível (35, 20) tem alpha 255 e verde
    assert arr[20, 35, 1] == 255
    assert arr[20, 35, 3] == 255


def test_mask_structure_undo_redo():
    """Valida transação de histórico com máscara de camada."""
    w, h = 64, 64
    facade = native.PaintEngineFacade(w, h)
    facade.add_layer("Base")

    assert not facade.has_layer_mask(0)

    # Inicia transação estrutural
    assert facade.begin_layer_transaction()
    facade.add_layer_mask(0)
    assert facade.has_layer_mask(0)
    facade.commit_layer_transaction()

    # Desfazer deve remover a máscara
    assert facade.undo()
    assert not facade.has_layer_mask(0)

    # Refazer deve restaurar a máscara
    assert facade.redo()
    assert facade.has_layer_mask(0)
