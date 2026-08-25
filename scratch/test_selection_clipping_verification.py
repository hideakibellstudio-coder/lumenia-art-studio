import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry
from ui.engine_backends.aladyn import AladynBackend

def run_test():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    print("=== TESTE: Verificação de Confinamento da Máscara de Seleção ===")
    backend = AladynBackend()
    backend.init_renderer(0, 800, 600, 800, 600)
    EngineRegistry.instance().setup([backend])

    dm = DocumentManager.instance()
    doc = dm.new_document(width=800, height=600, name="Selection Clipping Test")

    # 1. Cria uma seleção retangular em (200, 200, 200, 200)
    print("\n--- 1. Criando seleção retangular de (200, 200) até (400, 400) ---")
    ok_sel = backend.select_rect(200, 200, 200, 200)
    print(f"select_rect: {ok_sel}, has_selection: {backend.has_selection()}")
    assert backend.has_selection(), "Falha ao criar seleção!"

    # 2. Pinta um traço horizontal completo cruzando a tela de X=50 até X=650 na altura Y=300
    print("\n--- 2. Pintando traço de X=50 a X=650 (atravessando a seleção) ---")
    backend.start_stroke(50, 300, 1.0)
    for x in range(60, 660, 20):
        backend.paint_stroke(x, 300, 1.0)
    backend.end_stroke(650, 300)

    # 3. Inspeciona os pixels
    qimg = backend.get_qimage()
    assert qimg is not None and not qimg.isNull(), "QImage do backend nulo!"
    qimg.save("scratch/selection_clipping_test.png")

    # Ponto FORA da seleção à esquerda: (100, 300)
    col_outside_left = qimg.pixelColor(100, 300)
    print(f"Pixel FORA à esquerda (100, 300): {col_outside_left.name()}")
    assert col_outside_left.name() == "#ffffff", f"Vazamento de traço fora da seleção à esquerda! Cor={col_outside_left.name()}"

    # Ponto FORA da seleção à direita: (500, 300)
    col_outside_right = qimg.pixelColor(500, 300)
    print(f"Pixel FORA à direita (500, 300): {col_outside_right.name()}")
    assert col_outside_right.name() == "#ffffff", f"Vazamento de traço fora da seleção à direita! Cor={col_outside_right.name()}"

    # Ponto DENTRO da seleção: (300, 300)
    col_inside = qimg.pixelColor(300, 300)
    print(f"Pixel DENTRO da seleção (300, 300): {col_inside.name()}")
    assert col_inside.name() != "#ffffff" and col_inside.red() < 50, f"Falha na pintura dentro da seleção! Cor={col_inside.name()}"

    # 4. Testa com Seleção Elíptica e Inker Engine
    print("\n--- 3. Testando Seleção Elíptica com InkerEngine ---")
    backend.clear_canvas()
    backend.set_engine_type(2) # Inker
    backend.select_ellipse(400, 300, 100, 80) # Elipse no centro
    backend.start_stroke(100, 300, 1.0)
    for x in range(120, 700, 20):
        backend.paint_stroke(x, 300, 1.0)
    backend.end_stroke(700, 300)

    qimg2 = backend.get_qimage()
    qimg2.save("scratch/selection_ellipse_clipping.png")

    assert qimg2.pixelColor(250, 300).name() == "#ffffff", "Vazamento fora da elipse à esquerda!"
    assert qimg2.pixelColor(550, 300).name() == "#ffffff", "Vazamento fora da elipse à direita!"
    assert qimg2.pixelColor(400, 300).name() != "#ffffff", "Falha na pintura dentro da elipse!"

    print("\n[OK] CONFINAMENTO DE TODAS AS SELEÇÕES VALIDADO COM 100% DE SUCESSO!")

if __name__ == "__main__":
    run_test()
