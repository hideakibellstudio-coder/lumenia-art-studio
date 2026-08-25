import os
import sys

sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia")
sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\ALADYN ENGINE")

from PySide6 import QtCore, QtGui, QtWidgets
from plugins.system.workspace_core.workspace.secondary_tool_bar import SecondaryToolBar

app = QtWidgets.QApplication.instance()
if not app:
    app = QtWidgets.QApplication(sys.argv)

sec = SecondaryToolBar()
sec.set_tool("shapes")

# 1. Test Horizontal
sec.set_orientation(QtCore.Qt.Horizontal)
sec.show()
sec.adjustSize()
app.processEvents()

pix_h = QtGui.QPixmap(sec.size())
pix_h.fill(QtCore.Qt.transparent)
sec.render(pix_h)
pix_h.save("scratch/sec_toolbar_horizontal_preview.png")
print("Saved horizontal preview:", sec.size())

# 2. Test Vertical
sec.set_orientation(QtCore.Qt.Vertical)
sec.adjustSize()
app.processEvents()

pix_v = QtGui.QPixmap(sec.size())
pix_v.fill(QtCore.Qt.transparent)
sec.render(pix_v)
pix_v.save("scratch/sec_toolbar_vertical_preview.png")
print("Saved vertical preview:", sec.size())

# Test other tools in vertical
for t in ["eyedrop", "bucket", "wand", "transform", "lasso"]:
    sec.set_tool(t)
    sec.adjustSize()
    app.processEvents()

print("All orientations and tools passed without error!")
