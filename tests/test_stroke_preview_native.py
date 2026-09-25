"""Prévia nativa do pincel (render_stroke_preview) -- regressão de 2026-08-25.

A função sumiu do motor na decomposição do facade e o adaptador escondia a
ausência com `hasattr`: o painel de pincel passou 4 semanas mostrando um
desenho vetorial aproximado em vez do pincel real. Restaurada em 2026-09-22.
"""

from __future__ import annotations

import pytest

native = pytest.importorskip("aladyn_engine_native")


def _alfa_total(rgba: bytes) -> int:
    return sum(rgba[3::4])


@pytest.mark.parametrize("engine", ["Inker", "Pencil", "Marker", "Brush"])
def test_preview_desenha_o_traco_com_o_motor_real(engine):
    profile = native.BrushProfile()
    profile.engine_type = getattr(native.EngineType, engine)
    profile.brush_size = 24.0
    rgba = native.render_stroke_preview(profile, 260, 52)
    assert isinstance(rgba, bytes)
    assert len(rgba) == 260 * 52 * 4
    assert _alfa_total(rgba) > 0, f"motor {engine} não pintou nada na prévia"


def test_dimensoes_invalidas_devolvem_vazio():
    profile = native.BrushProfile()
    assert native.render_stroke_preview(profile, 0, 52) == b""
    assert native.render_stroke_preview(profile, 260, -1) == b""
    assert native.render_stroke_preview(profile, 100000, 52) == b""


def test_backend_entrega_a_previa_ao_painel():
    from PySide6.QtWidgets import QApplication
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    QApplication.instance() or QApplication(["--platform", "offscreen"])
    backend = AladynBackend()
    raw = backend.render_brush_preview(200, 40, {"size": 20.0, "engine_type": 1})
    assert raw is not None and len(raw) == 200 * 40 * 4


def test_previa_nao_altera_o_pincel_em_uso():
    """get_brush_profile() devolve referência ao perfil vivo: a prévia copia."""
    from PySide6.QtWidgets import QApplication
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    QApplication.instance() or QApplication(["--platform", "offscreen"])
    backend = AladynBackend()
    backend.set_active_document_context("previa_isolada", 256, 256)
    try:
        vivo = backend._facade.get_brush_profile()
        vivo.brush_size = 11.0
        vivo.opacity = 0.9
        backend.render_brush_preview(200, 40, {"size": 77.0, "opacity": 0.2, "engine_type": 1})
        assert vivo.brush_size == 11.0
        assert abs(vivo.opacity - 0.9) < 1e-9
    finally:
        backend.close_document_context("previa_isolada")


def _round_tip_mask(hardness: float) -> bytes:
    """A fórmula que a ponte calculava até 2026-09-25 (bind_stroke.cpp)."""
    size, center, max_dist = 64, 32.0, 30.0
    hard_span = min(max(hardness, 0.0), 0.99) * max_dist
    inv_soft = 1.0 / max(0.001, max_dist - hard_span)
    out = bytearray(size * size)
    for y in range(size):
        dy = y + 0.5 - center
        for x in range(size):
            dx = x + 0.5 - center
            dist = (dx * dx + dy * dy) ** 0.5
            if dist > max_dist:
                continue
            alpha = 1.0
            if dist > hard_span:
                t = min(max((max_dist - dist) * inv_soft, 0.0), 1.0)
                alpha = t * t * (3.0 - 2.0 * t)
            out[y * size + x] = int(min(max(alpha * 255.0, 0.0), 255.0))
    return bytes(out)


@pytest.mark.parametrize("hardness", [0.0, 0.35, 0.99, 1.5])
def test_round_tip_preview_is_computed_by_the_engine_with_the_same_numbers(hardness):
    """Sem textura de forma, a prévia da ponta é a máscara redonda do motor
    (boundary::renderRoundTipMask); o laço saiu da ponte sem mudar o resultado."""
    engine = native.PaintEngineFacade(8, 8)
    profile = engine.get_brush_profile()
    profile.hardness = hardness  # referência ao perfil do motor
    assert engine.get_shape_preview_dimensions() == (64, 64)
    assert engine.get_shape_preview_buffer() == _round_tip_mask(hardness)
