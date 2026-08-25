import os
import sys

sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia")
sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\ALADYN ENGINE")

from PySide6 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication.instance()
if not app:
    app = QtWidgets.QApplication(sys.argv)

from ui.core.widgets.shape_dropdown import ShapeDropdown, ShapeSelectorPopup, SHAPE_ITEMS
from ui.core.widgets.tool_options_widgets import ShapesOptionsWidget
from plugins.ui.brush_plugin.panel import BrushSettingsPanel
from plugins.system.workspace_core.workspace.secondary_tool_bar import SecondaryToolBar
from ui.core.tools import DEFAULT_TOOLS, TOOL_META

def test_shape_grid_dropdown():
    print("Testing ShapeDropdown and ShapeSelectorPopup...")
    dropdown = ShapeDropdown()
    assert dropdown.shape_id() == "shape_line", f"Expected default shape_line, got {dropdown.shape_id()}"
    assert "Linha Reta" in dropdown.text(), f"Expected 'Linha Reta' in text, got {dropdown.text()}"

    # Test popup
    popup = ShapeSelectorPopup()
    assert len(popup.buttons) == len(SHAPE_ITEMS) == 5, f"Expected 5 buttons, got {len(popup.buttons)}"
    
    # Test shape change
    dropdown.set_shape("shape_polygon", "Polígono")
    assert dropdown.shape_id() == "shape_polygon"

    print("ShapeDropdown OK!")

def test_shapes_options_widget():
    print("Testing ShapesOptionsWidget...")
    w = ShapesOptionsWidget()
    assert hasattr(w, "shape_dropdown"), "ShapesOptionsWidget should have shape_dropdown"
    assert w.shape_dropdown.shape_id() == "shape_line"
    assert w.spin_extra.isHidden(), "spin_extra should be hidden for shape_line"

    received_cfg = []
    w.settingsChanged.connect(lambda cfg: received_cfg.append(cfg))

    # Switch to rectangle
    w.shape_dropdown.set_shape("shape_rect", "Retângulo")
    w._on_shape_dropdown_changed("shape_rect", "Retângulo")
    assert not w.spin_extra.isHidden(), "spin_extra should not be hidden for shape_rect"
    assert w.lbl_extra.text() == "Cantos:"

    # Switch to polygon
    w.shape_dropdown.set_shape("shape_polygon", "Polígono")
    w._on_shape_dropdown_changed("shape_polygon", "Polígono")
    assert not w.spin_extra.isHidden()
    assert w.lbl_extra.text() == "Lados:"

    assert len(received_cfg) >= 2
    print("ShapesOptionsWidget OK!")

def test_brush_settings_panel_tool_column():
    print("Testing BrushSettingsPanel tool column...")
    panel = BrushSettingsPanel()
    assert len(panel._tool_buttons) == len(DEFAULT_TOOLS) == 10, f"Expected 10 buttons in sidebar, got {len(panel._tool_buttons)}"
    
    # Check that individual shape sub-tools are NOT in the column
    assert "shape_rect" not in panel._tool_buttons
    assert "shape_line" not in panel._tool_buttons
    assert "shapes" in panel._tool_buttons

    # Select shapes tool
    panel.set_tool_active("shapes")
    assert panel._tool_buttons["shapes"].isChecked()
    assert panel.stacked_tool_props.currentWidget() == panel.shapes_options_widget

    print("BrushSettingsPanel tool column OK!")

def test_secondary_toolbar_shapes():
    print("Testing SecondaryToolBar shapes panel...")
    sec = SecondaryToolBar()
    assert hasattr(sec, "shape_dropdown")
    sec.set_tool("shapes")
    assert sec.shape_dropdown.shape_id() == "shape_line"
    print("SecondaryToolBar shapes panel OK!")

if __name__ == "__main__":
    test_shape_grid_dropdown()
    test_shapes_options_widget()
    test_brush_settings_panel_tool_column()
    test_secondary_toolbar_shapes()
    print("ALL TESTS PASSED SUCCESSFULLY!")
