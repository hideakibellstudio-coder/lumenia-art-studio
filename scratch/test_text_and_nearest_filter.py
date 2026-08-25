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
    app.setAttribute(QtCore.Qt.AA_DontUseNativeMenuBar, True)

    print("=== TESTE 1: Inicializando Documento e Backend Aladyn ===")
    backend = AladynBackend()
    backend.init_renderer(0, 800, 600, 800, 600)
    EngineRegistry.instance().setup([backend])

    dm = DocumentManager.instance()
    doc = dm.new_document(width=800, height=600, name="Pixel Test Canvas")

    parent = QtWidgets.QWidget()
    parent.resize(800, 600)
    cw = CanvasWidget(parent)
    cw.resize(800, 600)
    cw.show()
    app.processEvents()

    print("=== TESTE 2: Desenhando um traço nativo e inserindo texto ===")
    # 1. Desenha um traço com o pincel nativo em (200, 200) até (400, 250)
    cw.start_stroke(200, 200, 1.0)
    cw.paint_stroke(300, 220, 1.0)
    cw.paint_stroke(400, 250, 1.0)
    cw.end_stroke(400, 250)
    app.processEvents()

    # 2. Insere um texto em (150, 100)
    cw.open_text_editor(150, 100)
    cw._active_text_editor.text_edit.setPlainText("ALADYN NATIVE TEXT")
    cw.set_text_settings({
        "font_family": "Segoe UI",
        "font_size": 32,
        "bold": True,
        "italic": False,
        "underline": False,
        "align": "left",
        "color": QtGui.QColor("#000000")
    })
    cw.commit_text_overlay()
    app.processEvents()

    # 3. Verifica se os pixels do texto foram gravados DIRETAMENTE nos tiles C++
    print("=== TESTE 3: Verificando se os pixels do texto estao na camada ativa C++ ===")
    assert len(cw._flood_layers) == 0, f"Texto nao deveria estar em _flood_layers, mas sim nos tiles C++! Encontrado: {len(cw._flood_layers)}"

    qimg = backend.get_qimage()
    assert qimg is not None and not qimg.isNull(), "QImage do backend C++ nulo!"
    qimg.save("scratch/qimage_raw.png")
    print(f"[OK] QImage salvo com dimensões {qimg.width()}x{qimg.height()} em scratch/qimage_raw.png")

    # Verifica amostragem de pixel na regiao do texto (ex: 160, 110)
    # Deve haver pixels nao-transparentes gravados nos tiles nativos
    has_text_pixels = False
    for y in range(100, 150):
        for x in range(150, 300):
            pixel = qimg.pixelColor(x, y)
            if pixel.alpha() > 100:
                has_text_pixels = True
                break
        if has_text_pixels:
            break

    assert has_text_pixels, "Nenhum pixel de texto encontrado no buffer nativo C++!"
    print("[OK] Pixels de texto gravados com sucesso nos tiles da camada ativa C++!")

    print("\n=== TESTE 4: Verificando Renderizacao com Nearest Neighbor em Alto Zoom (Estilo Paint Tool SAI) ===")
    cw.view_initialized = True
    cw.zoom = 20.0
    cw.pan_x = (cw.canvas_w / 2.0 - 180.0) * cw.zoom
    cw.pan_y = (cw.canvas_h / 2.0 - 110.0) * cw.zoom
    trans = cw._get_canvas_transform()
    screen_pt = trans.map(QtCore.QPointF(180, 110))
    print(f"Ponto (180, 110) mapeia na tela para: ({screen_pt.x()}, {screen_pt.y()}) [Widget: {cw.width()}x{cw.height()}]")

    cw.update()
    app.processEvents()

    pix_zoomed = QtGui.QPixmap(cw.size())
    cw.render(pix_zoomed)
    pix_zoomed.save("scratch/zoomed_nearest_sai_style.png")
    print("[OK] Salvo preview com filtro Nearest Neighbor em scratch/zoomed_nearest_sai_style.png")

    # Close-up no traço do pincel em (300, 220)
    cw.pan_x = (cw.canvas_w / 2.0 - 300.0) * cw.zoom
    cw.pan_y = (cw.canvas_h / 2.0 - 220.0) * cw.zoom
    cw.update()
    app.processEvents()
    pix_stroke = QtGui.QPixmap(cw.size())
    cw.render(pix_stroke)
    pix_stroke.save("scratch/zoomed_nearest_stroke_sai_style.png")
    print("[OK] Salvo preview do traço com filtro Nearest Neighbor em scratch/zoomed_nearest_stroke_sai_style.png")

    print("\n=== TODOS OS TESTES PASSARAM COM 100% DE SUCESSO! ===")

if __name__ == "__main__":
    run_test()
