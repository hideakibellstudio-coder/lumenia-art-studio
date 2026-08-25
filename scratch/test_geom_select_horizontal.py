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
sec.set_orientation(QtCore.Qt.Horizontal)

# Test the selection tool as shown in user's image
sec.set_tool("rect_select")
sec.btn_geom_aa_h.setChecked(True)
sec.show()
sec.adjustSize()
app.processEvents()

pix = QtGui.QPixmap(sec.size())
pix.fill(QtCore.Qt.transparent)
sec.render(pix)
pix.save("scratch/geom_select_horizontal_verified.png")
print("Saved selection tool preview:", sec.size())

# Test shapes tool
sec.set_tool("shapes")
sec.adjustSize()
app.processEvents()

pix_s = QtGui.QPixmap(sec.size())
pix_s.fill(QtCore.Qt.transparent)
sec.render(pix_s)
pix_s.save("scratch/shapes_horizontal_verified.png")
print("Saved shapes tool preview:", sec.size())
