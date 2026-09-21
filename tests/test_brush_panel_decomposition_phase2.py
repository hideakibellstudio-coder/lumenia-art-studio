"""Tests for Phase 2: BrushSettingsPanel ARCcC v2 decomposition."""

import pytest
from PySide6 import QtCore, QtWidgets, QtGui

from plugins.ui.brush_plugin.panel import BrushSettingsPanel
from plugins.ui.brush_plugin.components.tool_selection_column import ToolSelectionColumn
from plugins.ui.brush_plugin.components.quick_sliders_section import QuickSlidersSection
from ui.core.widgets.compact_slider import CompactSlider


@pytest.fixture(scope="session")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_tool_selection_column(qapp):
    col = ToolSelectionColumn()
    assert len(col.tool_buttons) >= 6
    assert "brush" in col.tool_buttons
    assert "eraser" in col.tool_buttons

    activated_tools = []
    col.toolActivated.connect(activated_tools.append)

    col.set_tool_active("eraser")
    assert col.tool_buttons["eraser"].isChecked()
    assert not col.tool_buttons["brush"].isChecked()

    col._on_btn_clicked("brush")
    assert "brush" in activated_tools
    assert col.tool_buttons["brush"].isChecked()


def test_quick_sliders_section(qapp):
    sec = QuickSlidersSection()
    assert len(sec.all_sliders) == 8
    assert isinstance(sec.size_slider, CompactSlider)
    assert isinstance(sec.opacity_slider, CompactSlider)

    emitted_size = []
    emitted_opacity = []
    sec.sizeChanged.connect(emitted_size.append)
    sec.opacityChanged.connect(emitted_opacity.append)

    sec.size_slider.setValue(120)
    assert 120.0 in emitted_size

    sec.opacity_slider.setValue(80)
    assert 0.8 in emitted_opacity

    # Test pinned visibility
    assert sec.contrast_slider.isHidden()
    sec.set_pinned_visible("contrast", True)
    assert not sec.contrast_slider.isHidden()

    # Test sync helpers
    sec.sync_size(250)
    assert sec.size_slider.value() == 250


def test_brush_settings_panel_backwards_compatibility(qapp):
    panel = BrushSettingsPanel()

    # Properties
    assert panel.qs_size is panel.size_slider
    assert panel.qs_opacity is panel.opacity_slider
    assert panel.contrast_slider is not None
    assert panel.pressure_slider is not None
    assert panel.curve_slider is not None
    assert panel.stabilizer_slider is not None
    assert panel.spacing_slider is not None
    assert panel.min_density_slider is not None
    assert panel.lbl_quick is not None
    assert len(panel._quick_sliders) == 8
    assert "brush" in panel._tool_buttons
    assert panel.tool_col_box is panel.tool_column

    # Signals
    emitted_sizes = []
    panel.sizeChanged.connect(emitted_sizes.append)
    panel.size_slider.setValue(45)
    assert 45.0 in emitted_sizes

    # Tool activation
    emitted_tools = []
    panel.toolActivated.connect(emitted_tools.append)
    panel.set_tool_active("eraser")
    assert panel.tool_column.tool_buttons["eraser"].isChecked()

    # Preset application
    preset_mock = {
        "brush_size": 99,
        "opacity": 0.75,
        "stabilizer_weight": 0.42,
        "spacing_factor": 0.15,
        "brush_grain_contrast": 1.5,
    }
    panel._on_preset_changed("test_preset", preset_mock)
    assert panel.size_slider.value() == 99
    assert panel.opacity_slider.value() == 75
