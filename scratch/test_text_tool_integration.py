import os
import sys

# Garante path da aplicação
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.theme.manager import ThemeManager
from ui.core.document.manager import DocumentManager
from plugins.system.workspace_core.workspace.floating_toolbar import FloatingToolbar
from plugins.system.workspace_core.workspace.secondary_tool_bar import SecondaryToolBar
from plugins.system.workspace_core.workspace.canvas.render_widget import CanvasWidget, TextOverlayEditor

def run_text_tool_tests():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setAttribute(QtCore.Qt.AA_DontUseNativeMenuBar, True)

    print("=== TESTE 1: FloatingToolbar possui botão 'text' ===")
    parent_widget = QtWidgets.QWidget()
    parent_widget.resize(1200, 800)

    ft = FloatingToolbar(parent_widget)
    ft.show()

    assert "text" in ft.buttons, f"Botao 'text' nao encontrado em FloatingToolbar: {list(ft.buttons.keys())}"
    print("[OK] FloatingToolbar possui botao 'text' com sucesso!")

    print("\n=== TESTE 2: SecondaryToolBar constroi painel de texto (H & V) ===")
    st = SecondaryToolBar(parent_widget)
    st.set_tool("text")
    st.set_orientation(QtCore.Qt.Horizontal)
    st.show()
    app.processEvents()

    assert "text" in st._panels_h, "Painel horizontal de texto nao encontrado!"
    assert "text" in st._panels_v, "Painel vertical de texto nao encontrado!"
    assert st.cbo_text_font_h.count() > 0, "Nenhuma fonte carregada no combobox horizontal!"
    assert st.spin_text_size_h.value() == 36, "Tamanho de fonte padrao incorreto!"
    print(f"[OK] SecondaryToolBar inicializou com {st.cbo_text_font_h.count()} fontes do sistema!")

    # Renderiza preview da barra secundaria na horizontal
    pix_h = st.grab()
    pix_h.save("scratch/text_secondary_toolbar_h.png")
    print("[OK] Salvo preview horizontal em scratch/text_secondary_toolbar_h.png")

    # Muda para vertical e renderiza preview
    st.set_orientation(QtCore.Qt.Vertical)
    app.processEvents()
    pix_v = st.grab()
    pix_v.save("scratch/text_secondary_toolbar_v.png")
    print("[OK] Salvo preview vertical em scratch/text_secondary_toolbar_v.png")

    print("\n=== TESTE 3: CanvasWidget In-Place Text Editing & Commit ===")
    dm = DocumentManager.instance()
    doc = dm.new_document(width=1200, height=800, name="Text Test Canvas")

    cw = CanvasWidget(parent_widget)
    cw.resize(1200, 800)
    cw.show()
    app.processEvents()

    # Seleciona ferramenta de texto
    cw.active_tool = "text"

    # Abre editor de texto in-place em (150, 200)
    cw.open_text_editor(150, 200)
    assert cw._active_text_editor is not None, "Editor de texto in-place nao foi instanciado!"
    print("[OK] Editor de texto in-place aberto com sucesso!")

    # Define conteudo e configuracoes tipograficas
    cw._active_text_editor.text_edit.setPlainText("LUMENIA STUDIO\nMotor Tipografico In-Place de Alta Fidelidade")
    cw.set_text_settings({
        "font_family": "Segoe UI",
        "font_size": 42,
        "bold": True,
        "italic": False,
        "underline": False,
        "align": "left",
        "color": QtGui.QColor("#9333ea")
    })
    app.processEvents()

    # Verifica se overlay acompanhou as mudancas
    assert cw._active_text_editor.get_plain_text().startswith("LUMENIA STUDIO")
    print("[OK] Texto e tipografia aplicados ao editor overlay!")

    # Renderiza preview com editor in-place aberto
    cw.update()
    app.processEvents()
    pix_editor = cw.grab()
    pix_editor.save("scratch/text_canvas_with_editor.png")
    print("[OK] Salvo preview com editor aberto em scratch/text_canvas_with_editor.png")

    # Confirma o texto para rasterizacao na camada ativa
    initial_layers_count = len(cw._flood_layers)
    cw.commit_text_overlay()

    assert cw._active_text_editor is None, "Editor de texto nao foi fechado apos commit!"
    assert len(cw._flood_layers) == initial_layers_count + 1, "Camada de texto nao foi adicionada ao canvas!"
    print("[OK] Texto commitado e rasterizado com sucesso no canvas!")

    # Renderiza preview final do canvas com o texto rasterizado
    cw.update()
    app.processEvents()
    pix_final = cw.grab()
    pix_final.save("scratch/text_canvas_committed.png")
    print("[OK] Salvo preview do canvas final em scratch/text_canvas_committed.png")

    print("\n=== TODOS OS TESTES PASSARAM COM 100% DE SUCESSO! ===")

if __name__ == "__main__":
    run_text_tool_tests()
