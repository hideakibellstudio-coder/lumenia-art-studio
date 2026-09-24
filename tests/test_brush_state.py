"""Contrato de ui/core/state: BrushState (fonte única) e BrushEngineSync (único caminho ao motor)."""

from __future__ import annotations

import math

import pytest
from PySide6 import QtGui

from ui.core.plugins.registry import ServiceRegistry
from ui.core.state import (
    BRUSH_PARAM_DEFAULTS,
    BrushEngineSync,
    BrushParam,
    BrushState,
    install_app_state,
    quick_params_from_preset,
    require,
)


class _RecordingBackend:
    """Registra as chamadas que o BrushEngineSync faz, na ordem."""

    def __init__(self):
        self.calls: list[tuple] = []

    def __getattr__(self, name):
        if not name.startswith(("set_", "apply_")):
            raise AttributeError(name)
        return lambda *args: self.calls.append((name, *args))


def test_defaults_cover_every_param():
    state = BrushState()
    assert set(state.snapshot()) == set(BrushParam)
    assert state.snapshot() == BRUSH_PARAM_DEFAULTS
    assert state.color == QtGui.QColor(0, 0, 0)


def test_same_value_emits_nothing_so_views_never_loop():
    state = BrushState()
    seen = []
    state.paramChanged.connect(lambda p, v: seen.append((p, v)))
    state.colorChanged.connect(lambda c: seen.append(c.name()))

    state.set_value(BrushParam.SIZE, 60.0)  # igual ao padrão
    state.set_color(QtGui.QColor(0, 0, 0))  # igual ao padrão
    assert seen == []

    state.set_value(BrushParam.SIZE, 12)
    assert seen == [(BrushParam.SIZE, 12.0)]


def test_invalid_values_are_rejected_without_touching_state():
    state = BrushState()
    for param, bad in [
        (BrushParam.SIZE, "grande"),
        (BrushParam.SIZE, math.nan),
        (BrushParam.OPACITY, True),
        (BrushParam.PRESSURE_CURVE, 0.0),
        (BrushParam.INVERT_HEIGHT, 1),
    ]:
        with pytest.raises(ValueError):
            state.set_value(param, bad)
    with pytest.raises(ValueError):
        state.set_color(QtGui.QColor())
    assert state.snapshot() == BRUSH_PARAM_DEFAULTS


def test_color_getter_returns_a_copy():
    state = BrushState()
    color = state.color
    color.setRed(255)
    assert state.color == QtGui.QColor(0, 0, 0)


def test_preset_mapping_matches_what_the_panel_used_to_do():
    assert quick_params_from_preset({"brush_size": 10, "opacity": 0.5, "stabilizer": 0.2,
                                     "spacing_factor": 0.3, "hardness": 0.7}) == {
        BrushParam.SIZE: 10.0,
        BrushParam.OPACITY: 0.5,
        BrushParam.STABILIZER: 0.2,
        BrushParam.SPACING: 0.3,
        BrushParam.CONTRAST: 0.7,
    }
    # brush_grain_contrast tem precedência sobre hardness.
    assert quick_params_from_preset({"brush_grain_contrast": 2.0, "hardness": 0.1})[BrushParam.CONTRAST] == 2.0


def test_preset_is_remembered_per_tool_and_applied_before_its_params():
    state = BrushState()
    order = []
    state.presetSelected.connect(lambda tool, name, data: order.append(("preset", tool, name)))
    state.paramChanged.connect(lambda p, v: order.append(("param", p)))

    state.select_preset("eraser", "Borracha Dura", {"brush_size": 16.0})
    assert order == [("preset", "eraser", "Borracha Dura"), ("param", BrushParam.SIZE)]
    assert state.preset("eraser") == ("Borracha Dura", {"brush_size": 16.0})
    assert state.preset("brush") is None


def test_sync_is_the_only_path_to_the_engine():
    state = BrushState()
    backend = _RecordingBackend()
    sync = BrushEngineSync(state, lambda: backend)  # noqa: F841 -- manter viva a conexão

    state.set_value(BrushParam.SIZE, 20)
    state.set_value(BrushParam.INVERT_HEIGHT, True)
    state.set_color(QtGui.QColor(255, 0, 0))
    state.select_preset("brush", "P", {"opacity": 0.5})

    assert backend.calls == [
        ("set_brush_size", 20.0),
        ("set_brush_invert_height", True),
        ("set_brush_color", 1.0, 0.0, 0.0),
        ("apply_brush_preset_dict", {"opacity": 0.5}),
        ("set_brush_opacity", 0.5),
    ]


def test_sync_without_backend_is_silent():
    state = BrushState()
    sync = BrushEngineSync(state, lambda: None)
    state.set_value(BrushParam.SIZE, 20)
    sync.resync("brush")


def test_resync_sends_preset_then_params_then_color():
    state = BrushState()
    backend = _RecordingBackend()
    sync = BrushEngineSync(state, lambda: backend)
    state.select_preset("brush", "P", {"brush_size": 80})
    state.set_value(BrushParam.SIZE, 100)  # usuário mexeu depois do preset
    backend.calls.clear()

    sync.resync("bucket")  # sem preset próprio: herda o do pincel

    names = [c[0] for c in backend.calls]
    assert names[0] == "apply_brush_preset_dict"
    assert names[-1] == "set_brush_color"
    assert ("set_brush_size", 100.0) in backend.calls
    assert len(names) == 1 + len(BrushParam) + 1


def test_install_app_state_is_idempotent_and_required_services_fail_loudly():
    registry = ServiceRegistry()
    first = install_app_state(registry, lambda: None)
    second = install_app_state(registry, lambda: None)
    assert first.brush is second.brush and first.brush_sync is second.brush_sync
    assert require(registry, BrushState) is first.brush
    with pytest.raises(RuntimeError, match="install_app_state"):
        require(ServiceRegistry(), BrushState)
