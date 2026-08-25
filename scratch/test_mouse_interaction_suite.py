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

def run_test():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    print("=== TESTE 1: Inicializando Documento e Backend Aladyn ===")
    backend = AladynBackend()
    backend.init_renderer(0, 800, 600, 800, 600)
    EngineRegistry.instance().setup([backend])

    dm = DocumentManager.instance()
    doc = dm.new_document(width=800, height=600, name="Full Interaction Test")

    cw = CanvasWidget()
    cw.resize(800, 600)
    cw.show()
    app.processEvents()

    # 1. Simula desenho de Retângulo via eventos de mouse reais
    print("\n=== TESTE 2: Simulação de Eventos de Mouse - Retângulo ===")
    cw.active_tool = "shapes"
    cw.set_shape_settings({
        "shape_type": "shape_rect",
        "draw_mode": "both",
        "stroke_width": 4,
        "stroke_color": QtGui.QColor(0, 0, 0, 255),
        "fill_color": QtGui.QColor(100, 200, 50, 255)
    })
    
    # Mouse Press em (100, 100)
    evt_press = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(100, 100), QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
    cw.mousePressEvent(evt_press)
    app.processEvents()

    # Mouse Move para (300, 250)
    evt_move = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, QtCore.QPointF(300, 250), QtCore.Qt.NoButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
    cw.mouseMoveEvent(evt_move)
    app.processEvents()

    # Mouse Release em (300, 250) -> chama _commit_shape_to_layer
    evt_release = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, QtCore.QPointF(300, 250), QtCore.Qt.LeftButton, QtCore.Qt.NoButton, QtCore.Qt.NoModifier)
    cw.mouseReleaseEvent(evt_release)
    app.processEvents()
    print("[OK] Retângulo desenhado e commitado via eventos de mouse sem exceção!")

    # 2. Simula desenho de Elipse via eventos de mouse reais
    print("\n=== TESTE 3: Simulação de Eventos de Mouse - Elipse ===")
    cw.set_shape_settings({
        "shape_type": "shape_ellipse",
        "draw_mode": "both",
        "stroke_width": 3,
        "stroke_color": QtGui.QColor(0, 0, 0, 255),
        "fill_color": QtGui.QColor(255, 100, 0, 255)
    })
    evt_press2 = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(400, 100), QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
    cw.mousePressEvent(evt_press2)
    evt_move2 = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, QtCore.QPointF(600, 300), QtCore.Qt.NoButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
    cw.mouseMoveEvent(evt_move2)
    evt_release2 = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, QtCore.QPointF(600, 300), QtCore.Qt.LeftButton, QtCore.Qt.NoButton, QtCore.Qt.NoModifier)
    cw.mouseReleaseEvent(evt_release2)
    app.processEvents()
    print("[OK] Elipse desenhada e commitada via eventos de mouse sem exceção!")

    # 3. Verifica buffer final C++
    qimg = backend.get_qimage()
    assert qimg is not None and not qimg.isNull(), "QImage do backend nulo!"
    qimg.save("scratch/mouse_suite_test.png")
    print(f"[OK] Imagem final salva em scratch/mouse_suite_test.png ({qimg.width()}x{qimg.height()})")

    print("\n=== TODOS OS TESTES PASSARAM COM 100% DE SUCESSO! ===")

if __name__ == "__main__":
    run_test()
