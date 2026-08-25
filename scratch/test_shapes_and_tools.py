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
    doc = dm.new_document(width=800, height=600, name="Shapes Test Canvas")

    cw = CanvasWidget()
    cw.resize(800, 600)
    cw.show()
    app.processEvents()

    print("\n=== TESTE 2: Desenhando Formas Geométricas (Retângulo e Elipse) ===")
    # 1. Retângulo com preenchimento azul e borda preta
    cw.active_tool = "shapes"
    cw.set_shape_settings({
        "shape_type": "shape_rect",
        "draw_mode": "both",
        "stroke_width": 4,
        "stroke_color": QtGui.QColor(0, 0, 0, 255),
        "fill_color": QtGui.QColor(0, 100, 255, 255),
        "corner_radius": 0
    })
    cw._shape_drag_start = QtCore.QPointF(50, 50)
    cw._shape_drag_current = QtCore.QPointF(200, 150)
    cw._commit_shape_to_layer()
    app.processEvents()

    # 2. Elipse com preenchimento vermelho
    cw.set_shape_settings({
        "shape_type": "shape_ellipse",
        "draw_mode": "both",
        "stroke_width": 3,
        "stroke_color": QtGui.QColor(0, 0, 0, 255),
        "fill_color": QtGui.QColor(255, 50, 50, 255)
    })
    cw._shape_drag_start = QtCore.QPointF(250, 50)
    cw._shape_drag_current = QtCore.QPointF(400, 200)
    cw._commit_shape_to_layer()
    app.processEvents()

    print("\n=== TESTE 3: Desenhando Texto Nativo ===")
    cw.open_text_editor(100, 300)
    cw._active_text_editor.text_edit.setPlainText("ALADYN NATIVE SHAPES & TEXT")
    cw.set_text_settings({
        "font_family": "Segoe UI",
        "font_size": 28,
        "bold": True,
        "color": QtGui.QColor(20, 20, 20, 255)
    })
    cw.commit_text_overlay()
    app.processEvents()

    print("\n=== TESTE 4: Verificando Pixels no Buffer Nativo C++ ===")
    qimg = backend.get_qimage()
    assert qimg is not None and not qimg.isNull(), "QImage do backend C++ nulo!"
    qimg.save("scratch/shapes_native_test.png")
    print(f"[OK] Buffer de pixels salvo em scratch/shapes_native_test.png ({qimg.width()}x{qimg.height()})")

    # Verifica pixel dentro do retângulo azul (100, 100)
    col_rect = qimg.pixelColor(100, 100)
    print(f"[OK] Pixel no retângulo (100, 100): RGBA({col_rect.red()}, {col_rect.green()}, {col_rect.blue()}, {col_rect.alpha()})")
    assert col_rect.blue() > 200 and col_rect.alpha() > 200, "Retângulo não foi gravado nos tiles C++!"

    # Verifica pixel dentro da elipse vermelha (325, 125)
    col_ellipse = qimg.pixelColor(325, 125)
    print(f"[OK] Pixel na elipse (325, 125): RGBA({col_ellipse.red()}, {col_ellipse.green()}, {col_ellipse.blue()}, {col_ellipse.alpha()})")
    assert col_ellipse.red() > 200 and col_ellipse.alpha() > 200, "Elipse não foi gravada nos tiles C++!"

    print("\n=== TODOS OS TESTES PASSARAM COM 100% DE SUCESSO! ===")

if __name__ == "__main__":
    run_test()
