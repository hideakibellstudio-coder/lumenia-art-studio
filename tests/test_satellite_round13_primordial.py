"""
Suíte de Integridade Orbital — Rodada 13: Sincronização Viewport/Navigator & Dirty Tracking
========================================================================================
Valida:
1. Atribuição de ícones SVG de flip no NavigatorControls alinhados com percepção do usuário.
2. Emissão de cameraChanged em RenderWidget.flip_x e flip_y (sincronização bidirecional Viewport <-> Navigator).
3. Rastreamento dirty completo (_mark_document_dirty) em mutações estruturais e visuais de camada (AladynLayerMixin).
4. Rastreamento dirty em resize, transações de camada, máscaras e recursos (aladyn.py, selection e resources mixins).
5. Governança estrita de tamanho de arquivos (ARCcC: limite < 450 LOC).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from PySide6 import QtWidgets, QtCore

from plugins.ui.navigator_plugin.panel import NavigatorPanel
from ui.engine_backends.aladyn_layer_mixin import AladynLayerMixin
from ui.engine_backends.aladyn import AladynBackend
from ui.engine_backends.aladyn_selection_mixin import AladynSelectionMixin
from ui.engine_backends.aladyn_resources_mixin import AladynResourcesMixin
from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget


@pytest.fixture(scope="module")
def app():
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(sys.argv)
    yield instance


# ── 1. Ícones e Sinais do Navigator ───────────────────────────────────────────

def test_navigator_flip_button_icons_and_signals(app):
    panel = NavigatorPanel()
    # Verifica propriedades de ícone atribuídas
    assert panel.controls.btn_fliph.property("icon_name") == "flip-vertical"
    assert panel.controls.btn_flipv.property("icon_name") == "flip-horizontal"

    # Garante paridade funcional 1:1 de sinais
    h_emitted = []
    v_emitted = []
    panel.controls.flipHRequested.connect(lambda: h_emitted.append(True))
    panel.controls.flipVRequested.connect(lambda: v_emitted.append(True))

    panel.controls.btn_fliph.click()
    assert len(h_emitted) == 1
    assert panel.state["flip_x"] is True

    panel.controls.btn_flipv.click()
    assert len(v_emitted) == 1
    assert panel.state["flip_y"] is True


# ── 2. Emissão de cameraChanged por flip_x / flip_y no Canvas ─────────────────

def test_render_widget_flip_camera_changed_emission(app):
    rw = RenderWidget()
    camera_events = []
    rw.cameraChanged.connect(lambda *args: camera_events.append(args))

    assert rw.flip_x is False
    assert rw.flip_y is False
    assert len(camera_events) == 0

    # 1. Altera flip_x -> deve emitir cameraChanged
    rw.flip_x = True
    assert rw.flip_x is True
    assert len(camera_events) == 1

    # 2. Reatribui mesmo valor -> idempotência (não deve reemitir)
    rw.flip_x = True
    assert len(camera_events) == 1

    # 3. Altera flip_y -> deve emitir cameraChanged
    rw.flip_y = True
    assert rw.flip_y is True
    assert len(camera_events) == 2

    # 4. Desfaz flip_x -> deve emitir cameraChanged
    rw.flip_x = False
    assert len(camera_events) == 3


# ── 3. Dirty Tracking em Operações de Camadas (AladynLayerMixin) ──────────────

class _MockLayerBackend(AladynLayerMixin):
    def __init__(self):
        self._facade = MagicMock()
        self._dirty_reasons = []

    def _mark_document_dirty(self, reason: str = "content"):
        self._dirty_reasons.append(reason)


def test_aladyn_layer_dirty_tracking():
    b = _MockLayerBackend()
    b._facade.add_layer.return_value = 1
    b._facade.remove_layer.return_value = True
    b._facade.duplicate_layer.return_value = 2
    b._facade.merge_layer_down.return_value = True
    b._facade.flatten_group.return_value = True
    b._facade.add_group.return_value = 3
    b._facade.add_filter_layer.return_value = 4
    b._facade.reorder_layer.return_value = True
    b._facade.reorder_layers.return_value = True
    b._facade.set_layer_parents.return_value = True

    b.add_layer("Camada Teste")
    assert "add_layer" in b._dirty_reasons

    b.remove_layer(1)
    assert "remove_layer" in b._dirty_reasons

    b.duplicate_layer(0)
    assert "duplicate_layer" in b._dirty_reasons

    b.merge_layer_down(1)
    assert "merge_layer_down" in b._dirty_reasons

    b.flatten_group(0)
    assert "flatten_group" in b._dirty_reasons

    b.add_group("Grupo Teste")
    assert "add_group" in b._dirty_reasons

    b.add_filter_layer("Filtro Teste", 0)
    assert "add_filter_layer" in b._dirty_reasons

    b.reorder_layer(0, 1)
    assert "reorder_layer" in b._dirty_reasons

    b.reorder_layers([1, 0])
    assert "reorder_layers" in b._dirty_reasons

    b.set_layer_parents([0, -1])
    assert "set_layer_parents" in b._dirty_reasons

    b.set_layer_blend_mode(0, 1)
    assert "blend_mode" in b._dirty_reasons

    b.set_layer_opacity(0, 0.5)
    assert "layer_opacity" in b._dirty_reasons

    b.set_layer_visibility(0, False)
    assert "layer_visibility" in b._dirty_reasons

    b.set_layer_lock(0, True)
    assert "layer_lock" in b._dirty_reasons

    b.set_layer_alpha_lock(0, True)
    assert "alpha_lock" in b._dirty_reasons

    b.set_layer_clipping_mask(0, True)
    assert "clipping_mask" in b._dirty_reasons

    b.set_layer_name(0, "Novo Nome")
    assert "layer_name" in b._dirty_reasons

    b.set_filter_params(0, [1.0, 2.0])
    assert "filter_params" in b._dirty_reasons


# ── 4. Dirty Tracking em Geometria, Transações e Recursos ─────────────────────

class _MockAladynBackend(AladynBackend):
    def __init__(self):
        self._native = MagicMock()
        self._facade = MagicMock()
        self._doc_facades = {}
        self._width = 800
        self._height = 600
        self._dirty_reasons = []

    def _mark_document_dirty(self, reason: str = "content"):
        self._dirty_reasons.append(reason)


def test_aladyn_geometry_and_transactions_dirty():
    backend = _MockAladynBackend()

    # 1. Resize
    backend.resize(1024, 768)
    assert "resize" in backend._dirty_reasons

    # 2. apply_prepared_geometry
    mock_prepared = MagicMock()
    backend._doc_facades["prep_1"] = mock_prepared
    backend._facade.apply_prepared_geometry.return_value = True
    backend._facade.get_width.return_value = 1024
    backend._facade.get_height.return_value = 768
    ok = backend.apply_prepared_geometry("prep_1")
    assert ok is True
    assert "prepared_geometry" in backend._dirty_reasons

    # 3. commit_layer_transaction
    backend._facade.commit_layer_transaction.return_value = 42
    step_id = backend.commit_layer_transaction()
    assert step_id == 42
    assert "layer_transaction" in backend._dirty_reasons


class _MockSelectionBackend(AladynSelectionMixin):
    def __init__(self):
        self._facade = MagicMock()
        self._dirty_reasons = []

    def _mark_document_dirty(self, reason: str = "content"):
        self._dirty_reasons.append(reason)


def test_aladyn_selection_mask_dirty():
    b = _MockSelectionBackend()
    b._facade.set_selection_mask_buffer.return_value = True
    res = b.set_selection_mask_buffer(b"\x00" * 64)
    assert res is True
    assert "selection" in b._dirty_reasons


class _MockResourcesBackend(AladynResourcesMixin):
    def __init__(self):
        self._facade = MagicMock()
        self._dirty_reasons = []
        self._canvas_texture = MagicMock()
        self._canvas_texture.canvas_grain_enabled = True
        self._canvas_texture.canvas_grain_scale = 1.0
        self._canvas_texture.canvas_grain_contrast = 1.0
        self._canvas_texture.canvas_grain_invert = False
        self._canvas_texture.canvas_texture_curve.get_lut.return_value = [0] * 256
        self._facade.get_canvas_texture.return_value = self._canvas_texture
        self._facade.get_canvas_height_texture.return_value = (64, 64, b"\x00" * (64 * 64))

    def _mark_document_dirty(self, reason: str = "content"):
        self._dirty_reasons.append(reason)


def test_aladyn_resources_dirty():
    b = _MockResourcesBackend()
    state = {
        "width": 64, "height": 64, "pixels": b"\x00" * (64 * 64),
        "enabled": True, "scale": 1.0, "contrast": 1.0, "invert": False,
        "curve": [0] * 256
    }
    ok = b.set_canvas_resource(state)
    assert ok is True
    assert "canvas_resource" in b._dirty_reasons


# ── 5. Governança de Tamanho de Arquivos (ARCcC < 450 LOC) ────────────────────

def test_round13_loc_governance():
    base_dir = Path(__file__).resolve().parent.parent
    files_to_check = [
        base_dir / "plugins/ui/navigator_plugin/panel.py",
        base_dir / "plugins/system/workspace_core/workspace/canvas/viewport/canvas_compat.py",
        base_dir / "ui/engine_backends/aladyn_layer_mixin.py",
        base_dir / "ui/engine_backends/aladyn.py",
        base_dir / "ui/engine_backends/aladyn_selection_mixin.py",
        base_dir / "ui/engine_backends/aladyn_resources_mixin.py",
        Path(__file__).resolve(),
    ]

    for path in files_to_check:
        assert path.is_file(), f"Arquivo não encontrado: {path}"
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines < 450, f"Arquivo {path.name} violou o limite verde (<450 LOC): {lines} linhas"
