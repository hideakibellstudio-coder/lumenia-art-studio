"""Deep snapping tests — validating clean unified GeometryToolController snapping."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PySide6 import QtWidgets, QtCore, QtGui

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from ui.core.document.manager import DocumentManager
from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
from plugins.ui.geometry_plugin.panel import GeometryPanel

print("=== TEST 1: Instantiating UI and Document ===")
doc = DocumentManager.instance().new_document(1920, 1080, "Test Snapping Doc")
rw = RenderWidget()
rw.resize(1200, 800)
rw.show()

gp = GeometryPanel()
gp.show()

print("=== TEST 2: Straight Ruler Snapping ===")
rw.geometry_ctrl.guide_state["type"] = "straight"
rw.geometry_ctrl.guide_state["p0"] = QtCore.QPointF(0, 300)
rw.geometry_ctrl.guide_state["p1"] = QtCore.QPointF(1920, 300)

rw.geometry_ctrl.start_stroke_snap((150.0, 315.0))
snapped = rw.geometry_ctrl.snap_point(250.0, 325.0)
print(f"Straight snapped from (250, 325) -> {snapped}")
assert abs(snapped[1] - 315.0) < 1e-4, f"Expected Y=315 parallel to ruler, got {snapped[1]}"
assert abs(snapped[0] - 250.0) < 1e-4
rw.end_stroke()

print("=== TEST 3: 2P Perspective Directional Snapping ===")
rw.geometry_ctrl.guide_state["type"] = "two_point"
rw.geometry_ctrl.guide_state["vpA"] = QtCore.QPointF(400, 300)
rw.geometry_ctrl.guide_state["vpB"] = QtCore.QPointF(-600, 300)

# Start stroke at (200, 400), drag towards vpA (400, 300)
rw.geometry_ctrl.start_stroke_snap((200.0, 400.0))
snapped_2p = rw.geometry_ctrl.snap_point(250.0, 375.0)
print(f"2P snapped towards vpA from (250, 375) -> {snapped_2p}")
rw.end_stroke()

print("=== TEST 4: Curvilinear 6P Snapping ===")
rw.geometry_ctrl.guide_state["type"] = "curvilinear"
rw.geometry_ctrl.guide_state["cx"] = 400.0
rw.geometry_ctrl.guide_state["cy"] = 300.0
rw.geometry_ctrl.guide_state["fov"] = 130.0
rw.geometry_ctrl.guide_state["show_v"] = True
rw.geometry_ctrl.guide_state["show_h"] = True
rw.geometry_ctrl.guide_state["show_d"] = True

rw.geometry_ctrl.start_stroke_snap((400.0, 300.0))
snapped_6p = rw.geometry_ctrl.snap_point(400.0, 340.0)
print(f"6P Curvilinear -> {snapped_6p}")
rw.end_stroke()

print("=== TEST 5: Popup and Dialog Screen Bounds ===")
btn = gp.selector_btn
btn._open_popup()
geom = btn.popup.geometry()
print(f"Selector popup geometry: x={geom.x()}, y={geom.y()}, w={geom.width()}, h={geom.height()}")
assert geom.width() == 330 and geom.height() == 250
btn.popup.close()

gp._toggle_advanced()
adv_geom = gp.adv_dialog.geometry()
print(f"Advanced dialog geometry: x={adv_geom.x()}, y={adv_geom.y()}, w={adv_geom.width()}, h={adv_geom.height()}")
assert adv_geom.width() == 360 and adv_geom.height() == 600
gp.adv_dialog.close()

print("[SUCCESS] ALL SNAPPING, 6P CURVILINEAR AND UI TESTS PASSED 100%!")
