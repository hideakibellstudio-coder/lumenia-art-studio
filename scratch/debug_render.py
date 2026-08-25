import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry
from ui.engine_backends.aladyn import AladynBackend
from plugins.system.workspace_core.workspace.canvas.render_widget import CanvasWidget

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
backend = AladynBackend()
backend.init_renderer(0, 800, 600, 800, 600)
EngineRegistry.instance().setup([backend])

dm = DocumentManager.instance()
doc = dm.new_document(width=800, height=600, name="Test")
print("Active doc:", dm.active_document())

cw = CanvasWidget()
cw.resize(800, 600)
cw.show()
app.processEvents()

# Stroke diretamente nas coordenadas de canvas
backend.start_stroke(200, 200, 1.0)
backend.paint_stroke(300, 220, 1.0)
backend.paint_stroke(400, 250, 1.0)
backend.end_stroke(400, 250)

# Insere texto nativo no canvas
cw.open_text_editor(150, 100)
cw._active_text_editor.text_edit.setPlainText("SAI PIXEL")
cw.set_text_settings({
    "font_family": "Segoe UI",
    "font_size": 36,
    "bold": True,
    "color": QtGui.QColor(0, 0, 0)
})
cw.commit_text_overlay()

# Foca no centro do traço em (300, 220) com zoom 24x
cw.zoom = 24.0
cw.pan_x = (cw.canvas_w / 2.0 - 300.0) * cw.zoom
cw.pan_y = (cw.canvas_h / 2.0 - 220.0) * cw.zoom
cw.update()
app.processEvents()

pix = QtGui.QPixmap(800, 600)
p = QtGui.QPainter(pix)
cw.render(p, QtCore.QPoint())
p.end()
pix.save("scratch/stroke_sai_comparison.png")
print("Saved scratch/stroke_sai_comparison.png focused on stroke at (300, 220)")
