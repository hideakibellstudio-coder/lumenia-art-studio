"""GeometryState: guias e simetria com uma cópia só (painel, diálogo e canvas são views).

Defeitos medidos em 2026-09-24, quando o painel guardava a própria cópia e a
empurrava inteira para o canvas:
- a simetria do documento A vazava para o B ao escolher uma régua no B;
- o painel mostrava a guia/simetria do documento anterior;
- mudar os segmentos no diálogo desfazia o ângulo arrastado no canvas;
- ângulo 0 escolhido no diálogo era ignorado.
"""
from __future__ import annotations

import os

import pytest
from PySide6 import QtWidgets

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["--platform", "offscreen"])

from ui.infrastructure.config import ConfigManager
from ui.infrastructure.i18n import tr
from ui.core.state import GeometryState


class _Recorder:
    def __init__(self, state: GeometryState) -> None:
        self.guide = self.symmetry = 0
        state.guideChanged.connect(self._on_guide)
        state.symmetryChanged.connect(self._on_symmetry)

    def _on_guide(self) -> None:
        self.guide += 1

    def _on_symmetry(self) -> None:
        self.symmetry += 1


# ── Regras do estado ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode, start, expected", [
    ("mirror_v", 30.0, 90.0), ("mirror_h", 30.0, 0.0),
    ("radial", 0.0, 90.0), ("radial", 45.0, 45.0), ("none", 0.0, 0.0),
])
def test_symmetry_mode_sets_the_axis_angle(mode, start, expected):
    state = GeometryState()
    state.symmetry["angle"] = start
    state.set_symmetry_mode(mode)
    assert (state.symmetry["mode"], state.symmetry["angle"]) == (mode, expected)


def test_advanced_fields_go_to_their_dictionary_and_only_changes_emit():
    state = GeometryState()
    state.set_guide_type("straight")
    state.set_symmetry_mode("mirror")
    calls = _Recorder(state)

    state.apply_advanced({"segments": 9, "hidden": True, "snap_mode": "v"})
    assert state.symmetry["segments"] == 9 and state.symmetry["hidden"] and state.guide["hidden"]
    assert state.guide["snap_mode"] == "v" and "snap_mode" not in state.symmetry
    assert (calls.guide, calls.symmetry) == (1, 1)

    state.apply_advanced({"segments": 9, "snap_mode": "v"})  # nada mudou
    assert (calls.guide, calls.symmetry) == (1, 1)


def test_editing_a_tab_with_nothing_active_turns_it_on():
    state = GeometryState()
    state.apply_advanced({"yaw": 45.0})
    assert state.guide["type"] == "curvilinear"
    state.apply_advanced({"segments": 8})
    assert state.symmetry["mode"] == "radial"
    other = GeometryState()
    other.apply_advanced({"snap_mode": "h"})  # aba de snap: não liga nada
    assert (other.guide["type"], other.symmetry["mode"]) == ("none", "none")


def test_load_starts_from_defaults_and_centers_on_the_document():
    state = GeometryState()
    state.apply_advanced({"yaw": 45.0, "segments": 12})
    calls = _Recorder(state)
    state.load(1000, 500, {"type": "straight"}, {"mode": "mirror"})
    assert state.guide["type"] == "straight" and state.guide["yaw"] == 0.0
    assert state.symmetry["mode"] == "mirror" and state.symmetry["segments"] == 6
    assert (state.symmetry["cx"], state.symmetry["cy"]) == (500.0, 250.0)
    assert state.guide["base_radius"] == pytest.approx(500 * 0.42)
    assert (calls.guide, calls.symmetry) == (1, 1)

    state.symmetry.update({"cx": 10.0, "cy": 10.0})
    state.center_pivot()
    assert (state.symmetry["cx"], state.symmetry["cy"]) == (500.0, 250.0)


def test_advanced_dialog_publishes_only_the_edited_field():
    from plugins.ui.geometry_plugin.components.advanced_settings_dialog import AdvancedGeometryDialog

    state = GeometryState()
    state.set_symmetry_mode("radial")
    state.symmetry["angle"] = 33.7  # arrasto livre no canvas, fora do passo do slider
    dialog = AdvancedGeometryDialog(None, state.fields())
    edits = []
    dialog.settingsChanged.connect(edits.append)
    try:
        dialog.slider_seg.setValue(8)
        assert edits == [{"segments": 8}]
    finally:
        dialog.deleteLater()


# ── Painel e canvas na janela principal ──────────────────────────────────────

@pytest.fixture
def workspace():
    from tests.main_window_fixture import main_window_com_workspace
    ConfigManager.instance().set_test_mode(True)
    mw = main_window_com_workspace()
    docs = []
    yield mw, mw.workspace.panel("geometry"), mw.workspace.canvas_widget.geometry_ctrl, docs
    for doc in docs:
        mw.dm.close_document(doc.uid)
    ConfigManager.instance().set_test_mode(False)


def test_symmetry_of_one_document_does_not_leak_into_another(workspace):
    mw, panel, ctrl, docs = workspace
    a = mw.dm.new_document(200, 200, "Geometria A")
    docs.append(a)
    panel.selector_btn.symmetry_changed.emit(5, "radial")
    assert a.sym_state["mode"] == "radial"

    b = mw.dm.new_document(200, 200, "Geometria B")
    docs.append(b)
    assert ctrl.sym_state["mode"] == "none"
    assert panel.lbl_status.text() == tr("geometry.status_idle")  # o painel mostra o B

    panel.selector_btn.ruler_changed.emit(1, "straight")
    assert ctrl.sym_state["mode"] == "none"
    assert b.sym_state.get("mode", "none") == "none"
    assert b.guide_state["type"] == "straight"
    assert a.sym_state["mode"] == "radial"


def test_dialog_edits_keep_the_angle_dragged_on_the_canvas(workspace):
    mw, panel, ctrl, docs = workspace
    docs.append(mw.dm.new_document(200, 200, "Ângulo"))
    panel.selector_btn.symmetry_changed.emit(5, "radial")
    panel._toggle_advanced()
    try:
        ctrl.sym_state["angle"] = 30.0  # alça arrastada no canvas
        assert panel.adv_dialog.slider_ang.value() == 30  # o diálogo aberto mostra
        panel.adv_dialog.slider_seg.setValue(8)
        assert (ctrl.sym_state["segments"], ctrl.sym_state["angle"]) == (8, 30.0)
        panel.adv_dialog.slider_ang.setValue(0)
        assert ctrl.sym_state["angle"] == 0.0
    finally:
        panel.adv_dialog.hide()


def test_menu_rulers_toggle_shows_in_the_panel(workspace):
    mw, panel, ctrl, docs = workspace
    docs.append(mw.dm.new_document(200, 200, "Menu"))
    mw.workspace.canvas_widget.toggle_rulers()
    assert ctrl.guide_state["type"] == "straight"
    assert tr("geometry.ruler_label", "Régua") in panel.lbl_status.text()
    assert panel.selector_btn.active_ruler_idx == 1
