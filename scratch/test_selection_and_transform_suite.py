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

    print("=== TESTE 1: Inicializando Backend e Documento ===")
    backend = AladynBackend()
    backend.init_renderer(0, 800, 600, 800, 600)
    EngineRegistry.instance().setup([backend])

    dm = DocumentManager.instance()
    doc = dm.new_document(width=800, height=600, name="Selection & Transform Suite")

    cw = CanvasWidget()
    cw.resize(800, 600)
    cw.show()
    app.processEvents()

    print("\n=== TESTE 2: Testando Seleção Retangular Nativa em C++ ===")
    ok = backend.select_rect(50, 50, 200, 150)
    print(f"select_rect(50, 50, 200, 150): {ok}, has_selection: {backend.has_selection()}")
    assert backend.has_selection(), "Falha ao criar seleção retangular!"
    bounds = backend.get_selection_bounds()
    print(f"Selection bounds: {bounds}")
    assert bounds == (50, 50, 200, 150), f"Bounds inesperados: {bounds}"

    print("\n=== TESTE 3: Preenchendo Seleção (Fill Selection) no ALADYN ENGINE ===")
    ok_fill = backend.fill_selection_on_active_layer(QtGui.QColor(0, 128, 255, 255))
    print(f"fill_selection_on_active_layer: {ok_fill}")
    assert ok_fill, "Falha ao preencher seleção!"

    backend.clear_selection()
    assert not backend.has_selection(), "Falha ao limpar seleção!"

    print("\n=== TESTE 4: Testando Transformação Livre Nativa (Transform Tool) ===")
    # Cria uma nova seleção para transformar
    backend.select_rect(50, 50, 200, 150)
    ok_trans = backend.begin_transform()
    print(f"begin_transform(): {ok_trans}, is_transform_active: {backend.is_transform_active()}")
    assert ok_trans and backend.is_transform_active(), "Falha ao iniciar transformação livre!"

    src_b = backend.get_transform_source_bounds()
    print(f"Transform source bounds: {src_b}")

    # Move 100px para a direita e rotaciona 15 graus
    ok_commit = backend.commit_transform(
        dx=100.0, dy=50.0, scale_x=1.2, scale_y=1.2,
        rotation_deg=15.0, pivot_x=src_b[0] + src_b[2]/2.0, pivot_y=src_b[1] + src_b[3]/2.0,
        flip_h=False, flip_v=False, interp_mode=2
    )
    print(f"commit_transform(): {ok_commit}, is_transform_active: {backend.is_transform_active()}")
    assert ok_commit, "Falha ao comitar transformação!"

    print("\n=== TESTE 5: Verificando Buffer Nativo Final ===")
    qimg = backend.get_qimage()
    assert qimg is not None and not qimg.isNull(), "QImage do backend nulo!"
    qimg.save("scratch/test_selection_and_transform.png")
    print(f"[OK] Imagem final salva em scratch/test_selection_and_transform.png ({qimg.width()}x{qimg.height()})")

    print("\n=== TODAS AS FERRAMENTAS DE SELEÇÃO E TRANSFORMAÇÃO VALIDADAS COM SUCESSO! ===")

if __name__ == "__main__":
    run_test()
