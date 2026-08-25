import os
import sys

sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia")
sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\ALADYN ENGINE")

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.widgets.shape_dropdown import ShapeSelectorPopup, ShapeDropdown
from plugins.ui.brush_plugin.panel import BrushSettingsPanel

app = QtWidgets.QApplication.instance()
if not app:
    app = QtWidgets.QApplication(sys.argv)

# Render ShapeSelectorPopup
popup = ShapeSelectorPopup()
popup.show()
popup.resize(260, 140)
app.processEvents()

pix = QtGui.QPixmap(popup.size())
pix.fill(QtCore.Qt.transparent)
popup.render(pix)
pix.save("scratch/shape_popup_preview.png")

# Render BrushSettingsPanel with Shapes active
panel = BrushSettingsPanel()
panel.resize(280, 500)
panel.set_tool_active("shapes")
panel.show()
app.processEvents()

pix_panel = QtGui.QPixmap(panel.size())
pix_panel.fill(QtCore.Qt.transparent)
panel.render(pix_panel)
pix_panel.save("scratch/shapes_panel_preview.png")

print("Saved preview images!")
