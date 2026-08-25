import os
import sys

sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia")
sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\ALADYN ENGINE")

from PySide6 import QtCore, QtGui, QtWidgets
from plugins.system.workspace_core.workspace.canvas.render_widget import CanvasWidget

app = QtWidgets.QApplication.instance()
if not app:
    app = QtWidgets.QApplication(sys.argv)

rw = CanvasWidget()
rw.resize(800, 600)
rw.canvas_w = 1920
rw.canvas_h = 1080
rw.show()
app.processEvents()

# 1. Test Initial Zoom
rw.zoom = 1.0
rw.pan_x = 0.0
rw.pan_y = 0.0
print("Initial Zoom:", rw.zoom, "Pan:", (rw.pan_x, rw.pan_y))

# 2. Test Anchored Zoom at cursor (200, 150)
cursor_pt = QtCore.QPointF(200, 150)
rw._apply_anchored_zoom(2.0, cursor_pt)
print("Zoom after 2x anchored at (200,150):", rw.zoom, "Pan:", (rw.pan_x, rw.pan_y))
assert abs(rw.zoom - 2.0) < 1e-4, f"Expected zoom 2.0, got {rw.zoom}"

# Check that canvas point under cursor remains invariant
p_canvas = rw.to_canvas(200, 150, 1.0, 0.0)

# Zoom in more
rw._apply_anchored_zoom(1.5, cursor_pt)
p_canvas_after = rw.to_canvas(200, 150, 1.0, 0.0)

print(f"Canvas point before: ({p_canvas.x:.2f}, {p_canvas.y:.2f}), after: ({p_canvas_after.x:.2f}, {p_canvas_after.y:.2f})")
diff = abs(p_canvas.x - p_canvas_after.x) + abs(p_canvas.y - p_canvas_after.y)
assert diff < 0.01, f"Anchored zoom failed! Point under cursor moved by {diff}"

# 3. Test Clamp Max (64.0) and Clamp Min (0.02)
rw._apply_anchored_zoom(100.0, cursor_pt)
print("Zoom clamped at max:", rw.zoom)
assert rw.zoom == 64.0, f"Expected 64.0 clamp, got {rw.zoom}"

rw._apply_anchored_zoom(0.0001, cursor_pt)
print("Zoom clamped at min:", rw.zoom)
assert rw.zoom == 0.02, f"Expected 0.02 clamp, got {rw.zoom}"

# 4. Test WheelEvent
rw.zoom = 1.0
rw.pan_x = 0.0
rw.pan_y = 0.0
wheel_evt = QtGui.QWheelEvent(
    QtCore.QPointF(400, 300),
    QtCore.QPointF(400, 300),
    QtCore.QPoint(0, 0),
    QtCore.QPoint(0, 120),
    QtCore.Qt.NoButton,
    QtCore.Qt.NoModifier,
    QtCore.Qt.ScrollBegin,
    False
)
rw.wheelEvent(wheel_evt)
print("Zoom after wheel scroll up:", rw.zoom)
assert abs(rw.zoom - 1.15) < 1e-3, f"Expected 1.15, got {rw.zoom}"

# 5. Test Zoom Drag Interaction (Alt + Right Click Drag)
rw._handle_pointer_press(QtCore.QPointF(400, 300), QtCore.Qt.RightButton, 1.0, QtCore.Qt.AltModifier)
assert getattr(rw, "is_zoom_dragging", False) == True, "Zoom dragging state should be active"
rw._handle_pointer_move(QtCore.QPointF(450, 300), 1.0, QtCore.Qt.AltModifier)
rw._handle_pointer_release(QtCore.QPointF(450, 300), QtCore.Qt.RightButton, QtCore.Qt.AltModifier)
assert getattr(rw, "is_zoom_dragging", False) == False, "Zoom dragging state should be inactive after release"

print("All Zoom and Clamp tests passed 100% successfully!")
