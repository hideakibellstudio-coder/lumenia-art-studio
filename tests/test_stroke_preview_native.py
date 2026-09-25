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
