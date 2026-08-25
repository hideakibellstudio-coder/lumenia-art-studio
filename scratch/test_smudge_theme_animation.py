import os
import sys

sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia")
sys.path.insert(0, r"z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\ALADYN ENGINE")

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from plugins.system.workspace_core.workspace.secondary_tool_bar import SecondaryToolBar
from plugins.system.workspace_core.workspace.floating_toolbar import FloatingToolbar

app = QtWidgets.QApplication.instance()
if not app:
    app = QtWidgets.QApplication(sys.argv)

# 1. Test ThemeManager default
theme = ThemeManager.instance()
print("Default Theme:", theme.current_theme)
assert theme.current_theme == "lumenia_purple", f"Expected lumenia_purple, got {theme.current_theme}"

# 2. Test SecondaryToolBar Smudge Panel
sec = SecondaryToolBar()

# Horizontal
sec.set_orientation(QtCore.Qt.Horizontal)
sec.set_tool("smudge")
sec.show()
sec.adjustSize()
app.processEvents()

pix_h = QtGui.QPixmap(sec.size())
pix_h.fill(QtCore.Qt.transparent)
sec.render(pix_h)
pix_h.save("scratch/smudge_horizontal_verified.png")
print("Saved Smudge Horizontal preview:", sec.size())

# Vertical
sec.set_orientation(QtCore.Qt.Vertical)
sec.adjustSize()
app.processEvents()

pix_v = QtGui.QPixmap(sec.size())
pix_v.fill(QtCore.Qt.transparent)
sec.render(pix_v)
pix_v.save("scratch/smudge_vertical_verified.png")
print("Saved Smudge Vertical preview:", sec.size())

# 3. Test FloatingToolbar Smudge button and Animation
float_bar = FloatingToolbar()
float_bar.show()
app.processEvents()

print("FloatingToolbar tool IDs:", list(float_bar.buttons.keys()))
assert "smudge" in float_bar.buttons, "Smudge button not found in FloatingToolbar!"

# Test Collapse
float_bar._do_collapse()
app.processEvents()
# Let animation run
loop = QtCore.QEventLoop()
QtCore.QTimer.singleShot(300, loop.quit)
loop.exec()

print("Collapsed size:", float_bar.size())

# Test Expand
float_bar._do_expand()
app.processEvents()
loop = QtCore.QEventLoop()
QtCore.QTimer.singleShot(300, loop.quit)
loop.exec()

print("Expanded size:", float_bar.size())

pix_fb = QtGui.QPixmap(float_bar.size())
pix_fb.fill(QtCore.Qt.transparent)
float_bar.render(pix_fb)
pix_fb.save("scratch/floating_toolbar_with_smudge.png")
print("Saved FloatingToolbar with Smudge preview:", float_bar.size())

print("All tests passed 100% successfully!")
