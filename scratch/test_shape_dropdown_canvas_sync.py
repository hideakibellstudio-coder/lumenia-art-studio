import os
import sys

sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia")
sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\ALADYN ENGINE")

from PySide6 import QtCore, QtGui, QtWidgets
from plugins.system.workspace_core.workspace.secondary_tool_bar import SecondaryToolBar
from plugins.system.workspace_core.workspace.canvas.render_widget import CanvasWidget

app = QtWidgets.QApplication.instance()
if not app:
    app = QtWidgets.QApplication(sys.argv)

# 1. Test SecondaryToolBar visual previews with new comfortable 38px height
sec = SecondaryToolBar()
sec.set_tool("shapes")

# Horizontal (with Ellipse selected)
sec.shape_dropdown_h.set_shape("shape_ellipse", "Elipse")
sec.set_orientation(QtCore.Qt.Horizontal)
sec.show()
sec.adjustSize()
app.processEvents()

pix_h = QtGui.QPixmap(sec.size())
pix_h.fill(QtCore.Qt.transparent)
sec.render(pix_h)
pix_h.save("scratch/sec_toolbar_horizontal_38px.png")
print("Saved horizontal 38px preview:", sec.size())

# Vertical
sec.set_orientation(QtCore.Qt.Vertical)
sec.adjustSize()
app.processEvents()

pix_v = QtGui.QPixmap(sec.size())
pix_v.fill(QtCore.Qt.transparent)
sec.render(pix_v)
pix_v.save("scratch/sec_toolbar_vertical_38px.png")
print("Saved vertical 38px preview:", sec.size())

# 2. Test CanvasWidget Shape Path calculation when changing shapes
cw = CanvasWidget()
cw.active_tool = "shapes"
cw._shape_drag_start = QtCore.QPointF(100, 100)
cw._shape_drag_current = QtCore.QPointF(300, 200)

for shape_id, expected_type in [
    ("shape_line", "Line"),
    ("shape_rect", "Rect"),
    ("shape_ellipse", "Ellipse"),
    ("shape_polygon", "Polygon"),
    ("shape_star", "Star")
]:
    cw.set_shape_settings({"shape_type": shape_id})
    path = cw._calculate_shape_path()
    assert path is not None and not path.isEmpty(), f"Path for {shape_id} should not be empty!"
    print(f"Verified {shape_id}: Path generated successfully: {path.boundingRect()}")

print("All shape switches and renders passed 100% successfully!")
