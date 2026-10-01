"""Entrada da caneta e do teclado no canvas: `CanvasInputRouter` e `CanvasKeyRouter`.

É o caminho mais sensível do produto e tinha 29% de cobertura em 2026-09-25.
Estes testes usam o `RenderWidget` e o motor nativo reais e conferem, para
cada ferramenta, o que o roteador faz com apertar, arrastar e soltar: pan,
zoom por arraste, conta-gotas, balde, varinha, seleções, laço livre e
poligonal, formas, transformação, traço (inclusive a ponta borracha da caneta
e a linha reta com Shift) e as teclas (espaço, apagar, atalhos de seleção,
Enter/Esc/setas na transformação). Servem também de rede para dividir o
`RenderWidget` (pendência 11).
"""
from __future__ import annotations

import pytest
from PySide6 import QtCore, QtGui

pytest.importorskip("aladyn_engine_native")

from ui.core.engine.engine_type import EngineType  # noqa: E402
from ui.core.engine.registry import EngineRegistry  # noqa: E402
from ui.infrastructure.bridge_client.aladyn import AladynBackend  # noqa: E402
from ui.plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget  # noqa: E402

Qt = QtCore.Qt
NO_MOD = Qt.KeyboardModifier.NoModifier


@pytest.fixture
def canvas(qapp):
    if EngineRegistry.instance().get_backend() is None:
        EngineRegistry.instance().setup([AladynBackend()])
    widget = RenderWidget()
    widget.resize(400, 300)
    yield widget
    widget.close()
    widget.deleteLater()


def press(w, x, y, button=Qt.MouseButton.LeftButton, modifiers=NO_MOD, **kwargs):
    w.input_router.handle_pointer_press(QtCore.QPointF(x, y), button, 0.8, modifiers, **kwargs)


def move(w, x, y, modifiers=NO_MOD):
    w.input_router.handle_pointer_move(QtCore.QPointF(x, y), 0.8, modifiers)


def release(w, x, y, button=Qt.MouseButton.LeftButton, modifiers=NO_MOD):
    w.input_router.handle_pointer_release(QtCore.QPointF(x, y), button, modifiers)


def key(w, code, modifiers=NO_MOD, *, auto_repeat=False, release_event=False):
    kind = QtCore.QEvent.Type.KeyRelease if release_event else QtCore.QEvent.Type.KeyPress
    event = QtGui.QKeyEvent(kind, code, modifiers, "", auto_repeat)
    router = w.key_router
    return router.handle_key_release(event) if release_event else router.handle_key_press(event)


def recorder(monkeypatch, obj, name):
    calls = []
    monkeypatch.setattr(obj, name, lambda *args, **kwargs: calls.append(args))
    return calls


# ── Navegação ────────────────────────────────────────────────────────────────

def test_middle_button_pans_the_camera(canvas):
    press(canvas, 100, 100, Qt.MouseButton.MiddleButton)
    assert canvas.is_panning
    before = (canvas.pan_x, canvas.pan_y)
    move(canvas, 130, 90)
    assert (canvas.pan_x - before[0], canvas.pan_y - before[1]) == (30, -10)
    release(canvas, 130, 90, Qt.MouseButton.MiddleButton)
    assert not canvas.is_panning


def test_space_plus_left_button_pans_and_space_release_ends_the_mode(canvas):
    assert key(canvas, Qt.Key.Key_Space)
    assert canvas.is_space_held
    assert key(canvas, Qt.Key.Key_Space, auto_repeat=True), "repetição da tecla é consumida"
    press(canvas, 50, 50)
    assert canvas.is_panning and not canvas.drawing
    release(canvas, 60, 60)
    assert not canvas.is_panning
    assert key(canvas, Qt.Key.Key_Space, release_event=True)
    assert not canvas.is_space_held


def test_focus_out_releases_a_stuck_space_key(canvas):
    key(canvas, Qt.Key.Key_Space)
    canvas.key_router.handle_focus_out()
    assert not canvas.is_space_held


def test_alt_right_drag_zooms(canvas):
    press(canvas, 200, 150, Qt.MouseButton.RightButton, Qt.KeyboardModifier.AltModifier)
    assert canvas.is_zoom_dragging
    zoom = canvas.zoom
    move(canvas, 240, 150)
    assert canvas.zoom > zoom
    release(canvas, 240, 150, Qt.MouseButton.RightButton)
    assert not canvas.is_zoom_dragging


# ── Ferramentas de clique ────────────────────────────────────────────────────

def test_eyedrop_tool_and_alt_click_sample_while_pressed(canvas):
    canvas.active_tool = "eyedrop"
    press(canvas, 100, 100)
    assert canvas.eyedrop_ctrl.active
    move(canvas, 110, 100)
    assert canvas.eyedrop_ctrl.pos == QtCore.QPointF(110, 100)
    release(canvas, 110, 100)
    assert not canvas.eyedrop_ctrl.active

    canvas.active_tool = "brush"
    press(canvas, 100, 100, modifiers=Qt.KeyboardModifier.AltModifier)
    assert canvas.eyedrop_ctrl.active and not canvas.drawing
    release(canvas, 100, 100)


def test_bucket_and_wand_act_on_click(canvas, monkeypatch):
    fills = recorder(monkeypatch, canvas, "do_flood_fill")
    wands = recorder(monkeypatch, canvas.selection_ctrl, "do_magic_wand_select")
    canvas.active_tool = "bucket"
    press(canvas, 10, 20)
    canvas.active_tool = "wand"
    press(canvas, 30, 40)
    assert fills == [(10, 20)] and wands == [(30, 40)]


def test_rect_select_drags_a_preview_and_commits_on_release(canvas, monkeypatch):
    finished = recorder(monkeypatch, canvas.selection_ctrl, "finish_geom_selection")
    canvas.active_tool = "rect_select"
    press(canvas, 100, 100)
    assert canvas.selection_ctrl.drag_active
    start = canvas.selection_ctrl.drag_start
    move(canvas, 150, 130)
    assert canvas.selection_ctrl.drag_current != start
    release(canvas, 150, 130)
    assert not canvas.selection_ctrl.drag_active and finished == [()]


def test_shape_tool_opens_a_stroke_and_commits_on_release(canvas, monkeypatch):
    committed = recorder(monkeypatch, canvas.shape_ctrl, "commit_to_layer")
    started = []
    canvas.strokeStarted.connect(lambda: started.append(True))
    canvas.active_tool = "shape_rectangle"
    press(canvas, 100, 100)
    assert canvas.shape_ctrl.drag_active and started == [True]
    move(canvas, 140, 120)
    release(canvas, 140, 120)
    assert not canvas.shape_ctrl.drag_active and committed == [()]


def test_freehand_lasso_collects_points_and_finishes_on_release(canvas, monkeypatch):
    finished = recorder(monkeypatch, canvas.selection_ctrl, "finish_lasso_selection")
    canvas.active_tool = "lasso"
    canvas.selection_ctrl.lasso_settings["lasso_type"] = "freehand"
    press(canvas, 100, 100)
    assert canvas.selection_ctrl.lasso_is_drawing
    move(canvas, 100.5, 100)  # menos de 2 px: não vira ponto
    move(canvas, 120, 100)
    move(canvas, 120, 130)
    assert len(canvas.selection_ctrl.lasso_points) == 3
    release(canvas, 120, 130)
    assert not canvas.selection_ctrl.lasso_is_drawing and finished == [()]


def test_polygonal_lasso_adds_clicks_closes_on_first_point_and_right_click_clears(canvas, monkeypatch):
    finished = recorder(monkeypatch, canvas.selection_ctrl, "finish_lasso_selection")
    canvas.active_tool = "lasso"
    canvas.selection_ctrl.lasso_settings["lasso_type"] = "polygonal"
    for x, y in ((100, 100), (200, 100), (200, 200)):
        press(canvas, x, y)
    assert len(canvas.selection_ctrl.lasso_points) == 3
    move(canvas, 150, 180)
    assert canvas.selection_ctrl.lasso_hover_pt is not None
    press(canvas, 101, 101)  # perto do primeiro ponto: fecha
    assert finished == [()]

    canvas.selection_ctrl.lasso_points[:] = [QtCore.QPointF(1, 1)]
    press(canvas, 50, 50, Qt.MouseButton.RightButton)
    assert canvas.selection_ctrl.lasso_points == [] and canvas.selection_ctrl.lasso_hover_pt is None


def test_transform_tool_starts_the_transform_on_click(canvas, monkeypatch):
    started = []
    monkeypatch.setattr(canvas, "start_transform_mode", lambda: started.append(True) or True)
    canvas.active_tool = "transform"
    press(canvas, 100, 100)
    assert started == [True]


# ── Traço ────────────────────────────────────────────────────────────────────

def test_brush_stroke_press_move_release(canvas):
    canvas.active_tool = "brush"
    press(canvas, 100, 100)
    assert canvas.drawing
    move(canvas, 140, 110)
    release(canvas, 140, 110)
    assert not canvas.drawing


def test_eraser_tip_switches_the_engine_only_during_the_stroke(canvas):
    backend = EngineRegistry.instance().get_backend()
    before = backend.get_active_engine_type()
    assert before != EngineType.ERASER
    press(canvas, 100, 100, is_eraser_tip=True)
    # Era 6, o Borrar: o teste cravava o valor errado do código (D1, 2026-10-01).
    assert backend.get_active_engine_type() == EngineType.ERASER
    release(canvas, 120, 100)
    assert backend.get_active_engine_type() == before


def test_shift_click_draws_a_straight_line_from_the_last_stroke(canvas, monkeypatch):
    canvas.active_tool = "brush"
    press(canvas, 100, 100)
    release(canvas, 100, 100)
    painted = []
    original = canvas.paint_stroke
    monkeypatch.setattr(canvas, "paint_stroke", lambda *a, **k: painted.append(a[:2]) or original(*a, **k))
    press(canvas, 200, 100, modifiers=Qt.KeyboardModifier.ShiftModifier)
    assert len(painted) == 10 and painted[-1] == (200.0, 100.0)
    release(canvas, 200, 100)


# ── Teclado ──────────────────────────────────────────────────────────────────

def test_selection_shortcuts_and_delete(canvas):
    backend = EngineRegistry.instance().get_backend()
    assert key(canvas, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    assert backend.has_selection()
    assert key(canvas, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
    assert not backend.has_selection()
    assert not key(canvas, Qt.Key.Key_Delete), "sem seleção, Delete não é da viewport"

    backend.select_all()
    started, finished = [], []
    canvas.strokeStarted.connect(lambda: started.append(True))
    canvas.strokeFinished.connect(lambda: finished.append(True))
    assert key(canvas, Qt.Key.Key_Delete)
    assert started == finished == [True]
    backend.clear_selection()


def test_transform_keys_commit_cancel_and_nudge(canvas, monkeypatch):
    commits = recorder(monkeypatch, canvas, "commit_transform")
    cancels = recorder(monkeypatch, canvas, "cancel_transform")
    ctrl = canvas.transform_ctrl
    monkeypatch.setattr(ctrl, "active", True, raising=False)
    dx, dy = ctrl.dx, ctrl.dy
    assert key(canvas, Qt.Key.Key_Right)
    assert key(canvas, Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
    assert (ctrl.dx - dx, ctrl.dy - dy) == (1.0, 10.0)
    assert key(canvas, Qt.Key.Key_Return) and key(canvas, Qt.Key.Key_Escape)
    assert commits == [()] and cancels == [()]


@pytest.mark.parametrize("handle, shape", [
    ("move", Qt.CursorShape.SizeAllCursor), ("pivot", Qt.CursorShape.CrossCursor),
    ("rotate", Qt.CursorShape.PointingHandCursor), ("tl", Qt.CursorShape.SizeFDiagCursor),
    ("tr", Qt.CursorShape.SizeBDiagCursor), ("tc", Qt.CursorShape.SizeVerCursor),
    ("ml", Qt.CursorShape.SizeHorCursor),
])
def test_transform_handles_show_the_matching_cursor(canvas, handle, shape):
    canvas.input_router.update_transform_cursor(handle)
    assert canvas.cursor().shape() == shape
