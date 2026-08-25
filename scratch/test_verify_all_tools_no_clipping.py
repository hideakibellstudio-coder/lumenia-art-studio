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

tools = ["rect_select", "shapes", "bucket", "wand", "transform", "lasso", "eyedrop"]

# 1. Test Horizontal for all tools
sec.set_orientation(QtCore.Qt.Horizontal)
sec.show()

for t in tools:
    sec.set_tool(t)
    sec.adjustSize()
    app.processEvents()
    pix = QtGui.QPixmap(sec.size())
    pix.fill(QtCore.Qt.transparent)
    sec.render(pix)
    pix.save(f"scratch/verify_{t}_h.png")
    print(f"Verified Horizontal {t}: {sec.size()}")

# 2. Test Vertical for all tools
sec.set_orientation(QtCore.Qt.Vertical)
sec.adjustSize()

for t in tools:
    sec.set_tool(t)
    sec.adjustSize()
    app.processEvents()
    pix = QtGui.QPixmap(sec.size())
    pix.fill(QtCore.Qt.transparent)
    sec.render(pix)
    pix.save(f"scratch/verify_{t}_v.png")
    print(f"Verified Vertical {t}: {sec.size()}")

print("All tool renders completed!")
