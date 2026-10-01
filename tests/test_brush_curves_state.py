"""The Bézier curves of the brush live in BrushState, and only BrushEngineSync writes them (S0.4, D5).

The curve window used to keep the curves in its own widgets and push them to the
engine on every edit, a second writer next to BrushEngineSync. What that cost, all
visible: a new document got a facade with the default curves while the open window
still showed the old ones; selecting a preset could overwrite the enabled flags the
user had set; and nothing outside the window knew the curves existed.

Now the window edits the state and shows the state, and the sync is the only writer.
"""

from __future__ import annotations

import pathlib

import pytest

from ui.core.state import BrushEngineSync, BrushState
from ui.core.state.brush_curves import BrushCurve, CurveSetting, default_curve

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOFT = ((0.0, 0.0), (0.12, 0.52), (0.50, 0.88), (1.0, 1.0))
HARD = ((0.0, 0.0), (0.45, 0.10), (0.85, 0.45), (1.0, 1.0))


class RecordingBackend:
    """The part of EngineBackend the sync uses, recording every write in order."""

    def __init__(self):
        self.calls = []

    def set_curve_control_points(self, curve_type, points, enabled):
        self.calls.append(("curve", curve_type, [tuple(p) for p in points], enabled))

    def apply_brush_preset_dict(self, data):
        self.calls.append(("preset", dict(data)))

    def __getattr__(self, name):  # every other setter is a no-op for these tests
        return lambda *args, **kwargs: None


# -- the state ----------------------------------------------------------------

def test_every_curve_starts_at_its_default_and_is_not_edited():
    state = BrushState()
    for curve in BrushCurve:
        assert state.curve(curve) == default_curve(curve)
    assert state.edited_curves() == {}


def test_setting_a_curve_emits_once_and_an_equal_value_emits_nothing():
    state = BrushState()
    seen = []
    state.curveChanged.connect(lambda curve, setting: seen.append((curve, setting)))
    soft = CurveSetting(SOFT, True)
    state.set_curve(BrushCurve.PRESSURE_SIZE, soft)
    state.set_curve(BrushCurve.PRESSURE_SIZE, CurveSetting(SOFT, True))
    assert seen == [(BrushCurve.PRESSURE_SIZE, soft)]
    assert state.edited_curves() == {BrushCurve.PRESSURE_SIZE: soft}


@pytest.mark.parametrize(
    "points",
    [SOFT[:3], SOFT + ((1.0, 1.0),), ((0.0, 0.0), (float("nan"), 0.5), (0.5, 0.5), (1.0, 1.0)),
     ((0.0, 0.0), (1.5, 0.5), (0.5, 0.5), (1.0, 1.0))],
    ids=["three_points", "five_points", "nan", "outside_the_unit_square"],
)
def test_a_curve_the_engine_could_not_take_is_refused(points):
    with pytest.raises(ValueError):
        CurveSetting(tuple(points), True)


# -- the sync is the only writer ------------------------------------------------

def test_a_state_change_reaches_the_engine_through_the_sync():
    state, backend = BrushState(), RecordingBackend()
    sync = BrushEngineSync(state, lambda: backend)  # keep it alive: a QObject nobody holds is collected
    state.set_curve(BrushCurve.PRESSURE_FLOW, CurveSetting(HARD, False))
    assert backend.calls == [("curve", "pressure_flow", list(HARD), False)]
    assert sync is not None


def test_resync_sends_only_the_curves_the_user_edited():
    state, backend = BrushState(), RecordingBackend()
    sync = BrushEngineSync(state, lambda: backend)
    state.set_curve(BrushCurve.VELOCITY_SIZE, CurveSetting(SOFT, True))
    backend.calls.clear()
    sync.resync()
    assert [call for call in backend.calls if call[0] == "curve"] == [("curve", "velocity_size", list(SOFT), True)]


def test_a_preset_does_not_wipe_the_curves_the_user_set():
    """The preset is applied first; the user's curves go after it."""
    state, backend = BrushState(), RecordingBackend()
    sync = BrushEngineSync(state, lambda: backend)
    state.set_curve(BrushCurve.PRESSURE_SIZE, CurveSetting(SOFT, True))
    backend.calls.clear()
    state.select_preset("brush", "Pencil", {"brush_size": 12.0})
    assert sync is not None
    kinds = [call[0] for call in backend.calls]
    assert kinds.index("preset") < max(i for i, kind in enumerate(kinds) if kind == "curve")
    assert ("curve", "pressure_size", list(SOFT), True) in backend.calls


def test_no_module_of_the_ui_writes_curves_to_the_engine_except_the_sync():
    allowed = {
        "ui/core/state/brush_engine_sync.py",
        "ui/core/engine/backend.py",
        "ui/core/engine/backend_protocols.py",
        "ui/infrastructure/bridge_client/aladyn_brush_mixin.py",
    }
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "ui").rglob("*.py"))
        if ".set_curve_control_points(" in path.read_text(encoding="utf-8")
        and path.relative_to(ROOT).as_posix() not in allowed
    ]
    assert not offenders, f"a second writer of the brush curves: {offenders}"


# -- the window ---------------------------------------------------------------

def _window(qapp, monkeypatch):
    from ui.core.engine.registry import EngineRegistry

    def forbidden(*args, **kwargs):
        raise AssertionError("the curve window asked for the engine")

    monkeypatch.setattr(EngineRegistry, "instance", classmethod(forbidden))
    from ui.core.screens.curve_window import CurveWindow

    state = BrushState()
    return state, CurveWindow(state)


def test_the_window_edits_the_state_and_never_touches_the_engine(qapp, monkeypatch):
    state, window = _window(qapp, monkeypatch)
    window.pressure_sec.curve.set_preset("soft")
    assert state.curve(BrushCurve.PRESSURE_SIZE).points == SOFT
    window.velocity_sec.chk.setChecked(True)
    assert state.curve(BrushCurve.VELOCITY_SIZE).enabled is True


def test_the_window_shows_a_change_that_came_from_somewhere_else(qapp, monkeypatch):
    state, window = _window(qapp, monkeypatch)
    state.set_curve(BrushCurve.PRESSURE_FLOW, CurveSetting(HARD, False))
    assert tuple(window.flow_sec.curve.get_control_points()) == HARD
    assert window.flow_sec.active is False


def test_opening_the_window_writes_nothing(qapp, monkeypatch):
    """It used to push its own defaults onto the engine as soon as it was built."""
    state, _window_ = _window(qapp, monkeypatch)
    assert state.edited_curves() == {}


# -- the engine, with a document switch ----------------------------------------

def test_a_new_documents_engine_gets_the_curves_after_the_resync():
    native = pytest.importorskip("aladyn_engine_native", reason="native module not built here")
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    def lut_for(points):
        reference = native.PaintEngineFacade(8, 8).get_brush_profile().pressure_size_curve
        reference.set_control_points(*(native.Point2D(x, y) for x, y in points))
        return list(reference.get_lut())

    state, backend = BrushState(), AladynBackend()
    sync = BrushEngineSync(state, lambda: backend)
    backend.set_active_document_context("first", 64, 64)
    state.set_curve(BrushCurve.PRESSURE_SIZE, CurveSetting(SOFT, True))

    backend.set_active_document_context("second", 64, 64)  # a fresh facade, default curves
    fresh = list(backend._facade.get_brush_profile().pressure_size_curve.get_lut())
    assert fresh != lut_for(SOFT), "the test needs a facade whose curve differs from the user's"
    sync.resync()
    assert list(backend._facade.get_brush_profile().pressure_size_curve.get_lut()) == lut_for(SOFT)
