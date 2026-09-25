"""
Suíte de Integridade Orbital — Rodada 12: Navigator Flip & Fronteira Primordial C++
==================================================================================
Valida:
1. Alinhamento 1:1 dos botões de Flip do Navigator (Ícone <-> Tooltip <-> Sinal <-> Estado de Câmera).
2. Resiliência do guard de render options em AladynMdiMixin (sem condicionais inalcançáveis).
3. Rastreamento dirty completo (_mark_document_dirty) em mutações nativas de camada, histórico, traço e balde de tinta.
4. Governança estrita de tamanho de arquivos (ARCcC: limite < 450 LOC).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from PySide6 import QtWidgets, QtCore

from ui.plugins.panels.navigator_plugin.panel import NavigatorPanel
from ui.infrastructure.bridge_client.aladyn_mdi_mixin import AladynMdiMixin
from ui.infrastructure.bridge_client.aladyn_layer_mixin import AladynLayerMixin
from ui.infrastructure.bridge_client.aladyn_stroke_mixin import AladynStrokeMixin


@pytest.fixture(scope="module")
def app():
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(sys.argv)
    yield instance


# ── 1. Alinhamento dos Botões de Flip do Navigator ────────────────────────────

def test_navigator_flip_button_clicks_aligned(app):
    """
    Garante que o clique direto em btn_fliph acione flipHRequested (e altere flip_x),
    e o clique direto em btn_flipv acione flipVRequested (e altere flip_y).
    """
    panel = NavigatorPanel()
    emitted = []
    panel.flip_changed_by_user.connect(lambda fx, fy: emitted.append((fx, fy)))

    h_signals = []
    v_signals = []
    panel.controls.flipHRequested.connect(lambda: h_signals.append(True))
    panel.controls.flipVRequested.connect(lambda: v_signals.append(True))

    # Estado inicial
    assert panel.state["flip_x"] is False
    assert panel.state["flip_y"] is False

    # 1. Clique no botão de Flip Horizontal (btn_fliph)
    panel.controls.btn_fliph.click()
    assert len(h_signals) == 1
    assert len(v_signals) == 0
    assert panel.state["flip_x"] is True
    assert panel.state["flip_y"] is False
    assert emitted[-1] == (True, False)

    # 2. Clique no botão de Flip Vertical (btn_flipv)
    panel.controls.btn_flipv.click()
    assert len(h_signals) == 1
    assert len(v_signals) == 1
    assert panel.state["flip_x"] is True
    assert panel.state["flip_y"] is True
    assert emitted[-1] == (True, True)

    # 3. Desfazer Flip Horizontal clicando novamente em btn_fliph
    panel.controls.btn_fliph.click()
    assert len(h_signals) == 2
    assert len(v_signals) == 1
    assert panel.state["flip_x"] is False
    assert panel.state["flip_y"] is True
    assert emitted[-1] == (False, True)

    # 4. Desfazer Flip Vertical clicando novamente em btn_flipv
    panel.controls.btn_flipv.click()
    assert len(h_signals) == 2
    assert len(v_signals) == 2
    assert panel.state["flip_x"] is False
    assert panel.state["flip_y"] is False
    assert emitted[-1] == (False, False)


# ── 2. Guard Resiliente de Render Options em AladynMdiMixin ──────────────────

class _MockMdiBackend(AladynMdiMixin):
    def __init__(self):
        self._init_backend_state()
        self._native = MagicMock()
        self._render_options = {"low_latency": True, "linear_gamma": True, "deep_color": False}


def test_aladyn_mdi_render_options_guard_unified():
    backend = _MockMdiBackend()
    mock_facade = MagicMock()
    mock_facade.get_width.return_value = 800
    mock_facade.get_height.return_value = 600
    mock_facade.set_render_options = MagicMock()
    backend._native.PaintEngineFacade.return_value = mock_facade

    backend.set_active_document_context("doc_1", 800, 600)
    assert mock_facade.set_render_options.call_count >= 1
    mock_facade.set_render_options.assert_called_with(low_latency=True, linear_gamma=True, deep_color=False)


def test_aladyn_mdi_render_options_guard_granular_fallback():
    backend = _MockMdiBackend()
    class _LegacyFacade:
        def __init__(self):
            self.low_latency = None
            self.linear_gamma = None
            self.deep_color = None
        def set_low_latency(self, val): self.low_latency = val
        def set_linear_gamma(self, val): self.linear_gamma = val
        def set_deep_color(self, val): self.deep_color = val
        def set_undo_memory_limit_mb(self, mb): pass
        def set_undo_max_steps(self, steps): pass
        def get_canvas_texture(self): return None
        def get_width(self): return 800
        def get_height(self): return 600

    legacy_facade = _LegacyFacade()
    backend._native.PaintEngineFacade.return_value = legacy_facade

    backend.set_active_document_context("doc_2", 800, 600)
    assert legacy_facade.low_latency is True
    assert legacy_facade.linear_gamma is True
    assert legacy_facade.deep_color is False


# ── 3. Rastreamento Dirty em Operações Nativas ────────────────────────────────

class _MockLayerBackend(AladynLayerMixin):
    def __init__(self):
        self._init_backend_state()
        self._facade = MagicMock()
        self.dirty_reasons = []

    def _mark_document_dirty(self, reason):
        self.dirty_reasons.append(reason)


def test_layer_mixin_mark_document_dirty():
    backend = _MockLayerBackend()

    # clear_canvas
    backend.clear_canvas()
    assert backend._facade.clear_canvas.called
    assert "clear_canvas" in backend.dirty_reasons

    # clear_layer
    backend.clear_layer(2)
    backend._facade.clear_layer.assert_called_with(2)
    assert "clear_layer" in backend.dirty_reasons

    # undo bem-sucedido
    backend._facade.undo.return_value = True
    backend._facade.get_width.return_value = 800
    backend._facade.get_height.return_value = 600
    assert backend.undo() is True
    assert "undo" in backend.dirty_reasons

    # redo bem-sucedido
    backend._facade.redo.return_value = True
    assert backend.redo() is True
    assert "redo" in backend.dirty_reasons

    # undo com falha não marca dirty
    backend.dirty_reasons.clear()
    backend._facade.undo.return_value = False
    assert backend.undo() is False
    assert "undo" not in backend.dirty_reasons


class _DummyColorRGBA:
    def __init__(self, r=0, g=0, b=0, a=255):
        self.r, self.g, self.b, self.a = r, g, b, a


class _MockNative:
    ColorRGBA = _DummyColorRGBA


class _MockStrokeBackend(AladynStrokeMixin):
    def __init__(self):
        self._init_backend_state()
        self._facade = MagicMock()
        self._native = _MockNative()
        self.dirty_reasons = []

    def _mark_document_dirty(self, reason):
        self.dirty_reasons.append(reason)


def test_stroke_mixin_mark_document_dirty():
    backend = _MockStrokeBackend()

    # flood_fill bem-sucedido
    backend._facade.flood_fill.return_value = True
    res = backend.flood_fill(10, 10, (255, 0, 0, 255))
    assert res is True
    assert "flood_fill" in backend.dirty_reasons

    # fill_area bem-sucedido
    backend.dirty_reasons.clear()
    backend._facade.flood_fill.return_value = True
    res = backend.fill_area(20, 20, (0, 255, 0, 255))
    assert res is True
    assert "flood_fill" in backend.dirty_reasons

    # end_stroke
    backend.dirty_reasons.clear()
    backend._facade.is_telemetry_enabled.return_value = False
    backend._facade.end_stroke_raw = MagicMock(return_value=[0, 0, 10, 10])
    backend.end_stroke()
    assert "stroke" in backend.dirty_reasons


# ── 4. Governança ARCcC (LOC < 450) ──────────────────────────────────────────

def test_round12_loc_governance():
    base = Path(__file__).resolve().parent.parent
    files = [
        base / "ui" / "plugins" / "panels" / "navigator_plugin" / "panel.py",
        base / "ui" / "infrastructure" / "bridge_client" / "aladyn_mdi_mixin.py",
        base / "ui" / "infrastructure" / "bridge_client" / "aladyn_layer_mixin.py",
        base / "ui" / "infrastructure" / "bridge_client" / "aladyn_stroke_mixin.py",
        Path(__file__),
    ]

    for f in files:
        assert f.is_file(), f"Arquivo não encontrado: {f}"
        lines = f.read_text(encoding="utf-8").splitlines()
        loc = len(lines)
        assert loc < 450, f"Violação de Governança ARCcC: {f.name} possui {loc} linhas (máximo permitido: 450)."
