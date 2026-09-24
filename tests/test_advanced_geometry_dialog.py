"""Tests for Phase 3: AdvancedGeometryDialog ARCcC v2 decomposition."""

import pytest
from PySide6 import QtWidgets

from plugins.ui.geometry_plugin.components.advanced_settings_dialog import AdvancedGeometryDialog
from plugins.ui.geometry_plugin.components.curvilinear_perspective_page import CurvilinearPerspectivePage
from plugins.ui.geometry_plugin.components.snapping_guides_page import SnappingGuidesPage
from plugins.ui.geometry_plugin.components.symmetry_settings_page import SymmetrySettingsPage



def test_curvilinear_perspective_page_standalone(qapp):
    init_state = {"yaw": 45.0, "pitch": -15.0, "fov": 100.0, "show_cube": True}
    page = CurvilinearPerspectivePage(initial_state=init_state)

    assert page.slider_yaw.value() == 45
    assert page.slider_pitch.value() == -15
    assert page.slider_fov.value() == 100
    assert page.chk_cube.isChecked()

    emitted = []
    page.changed.connect(lambda: emitted.append(True))
    page.slider_yaw.setValue(90)
    assert len(emitted) > 0

    collected = {}
    page.collect_state(collected)
    assert collected["yaw"] == 90.0
    assert collected["show_cube"] is True


def test_snapping_guides_page_standalone(qapp):
    init_state = {"snap_mode": "h", "snap_sensitivity": 12, "show_hint": False}
    page = SnappingGuidesPage(initial_state=init_state)

    assert page.combo_snap_mode.currentIndex() == 2 # "h"
    assert page.slider_sens.value() == 12
    assert not page.chk_hint.isChecked()

    emitted = []
    page.changed.connect(lambda: emitted.append(True))
    page.slider_sens.setValue(20)
    assert len(emitted) > 0

    collected = {}
    page.collect_state(collected)
    assert collected["snap_sensitivity"] == 20.0
    assert collected["snap_mode"] == "h"


def test_symmetry_settings_page_standalone(qapp):
    init_state = {"segments": 8, "angle": 45.0, "locked": True}
    page = SymmetrySettingsPage(initial_state=init_state)

    assert page.slider_seg.value() == 8
    assert page.slider_ang.value() == 45
    assert page.chk_lock.isChecked()

    emitted = []
    page.changed.connect(lambda: emitted.append(True))
    page.slider_seg.setValue(12)
    assert len(emitted) > 0

    collected = {}
    page.collect_state(collected)
    assert collected["segments"] == 12
    assert collected["locked"] is True


def test_advanced_geometry_dialog_integration(qapp):
    dialog = AdvancedGeometryDialog()
    assert dialog.stack.count() == 3

    # Check delegated properties
    assert dialog.slider_yaw is dialog.curv_page.slider_yaw
    assert dialog.slider_sens is dialog.snap_page.slider_sens
    assert dialog.slider_seg is dialog.sym_page.slider_seg

    # State synchronization
    new_state = {
        "yaw": 180.0,
        "snap_mode": "v",
        "segments": 16,
    }
    dialog.sync_from_state(new_state)
    assert dialog.slider_yaw.value() == 180
    assert dialog.combo_snap_mode.currentIndex() == 1
    assert dialog.slider_seg.value() == 16

    # Reset defaults
    dialog._on_reset()
    assert dialog.slider_yaw.value() == 0
    assert dialog.slider_sens.value() == 3
    assert dialog.slider_seg.value() == 6
