"""
Testes de Integridade dos Subsistemas Satélites — Rodada 10 (ARCcC v2)
=====================================================================
Validações de:
- Cor do Balde de Tinta (do_flood_fill) e garantia de simetria de sinais via try/finally.
- Simetria de ciclo de vida do TextToolController (strokeStarted/strokeFinished).
- active_color e set_shape_color no RenderWidget e CanvasCompatMixin.
- Papel com fonte única no Document (set_paper): canvas e PaperLayerWidget são views.
- Sincronização de previews em clear_canvas via strokeStarted/strokeFinished.
"""

import pytest
from PySide6 import QtWidgets, QtCore, QtGui

from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
from ui.core.engine.registry import EngineRegistry
from ui.engine_backends.aladyn import AladynBackend


@pytest.fixture(scope="module")
def app():
    qapp = QtWidgets.QApplication.instance()
    if qapp is None:
        qapp = QtWidgets.QApplication([])
    backend = EngineRegistry.instance().get_backend()
    if backend is None:
        EngineRegistry.instance().setup([AladynBackend()])
    return qapp


def test_bucket_flood_fill_color_and_signal_symmetry(app, monkeypatch):
    """Garante que do_flood_fill utilize active_color e mantenha simetria de sinais."""
    rw = RenderWidget()
    started = []
    finished = []
    rw.strokeStarted.connect(lambda: started.append(True))
    rw.strokeFinished.connect(lambda: finished.append(True))

    captured_calls = []

    class MockBackend:
        def fill_area(self, **kwargs):
            captured_calls.append(kwargs)
            return True

    monkeypatch.setattr(EngineRegistry.instance(), "get_backend", lambda: MockBackend())

    # Testa cor personalizada aplicada ao balde de tinta
    custom_color = QtGui.QColor(255, 42, 100, 255)
    rw.active_color = custom_color
    rw.do_flood_fill(100, 100)

    assert len(started) == 1
    assert len(finished) == 1
    assert len(captured_calls) == 1
    assert captured_calls[0]["fill_color"] == custom_color

    # Testa garantia de try/finally quando fill_area retorna False
    class FailingBackend:
        def fill_area(self, **kwargs):
            return False

    monkeypatch.setattr(EngineRegistry.instance(), "get_backend", lambda: FailingBackend())
    rw.do_flood_fill(100, 100)
    assert len(started) == 2
    assert len(finished) == 2

    # Testa garantia quando o backend for None
    monkeypatch.setattr(EngineRegistry.instance(), "get_backend", lambda: None)
    rw.do_flood_fill(100, 100)
    assert len(started) == 3
    assert len(finished) == 3


def test_text_tool_controller_lifecycle_symmetry(app):
    """Garante que TextToolController emita strokeStarted ao abrir e strokeFinished ao fechar."""
    rw = RenderWidget()
    started = []
    finished = []
    rw.strokeStarted.connect(lambda: started.append(True))
    rw.strokeFinished.connect(lambda: finished.append(True))

    # 1. Abrir editor emite strokeStarted
    rw.open_text_editor(50, 50)
    assert len(started) == 1
    assert len(finished) == 0
    assert rw.tool_mgr.active_text_editor is not None

    # 2. Cancelar editor emite strokeFinished
    rw.cancel_text_overlay()
    assert len(started) == 1
    assert len(finished) == 1
    assert rw.tool_mgr.active_text_editor is None

    # 3. Abrir editor e confirmar vazio também emite strokeFinished
    rw.open_text_editor(50, 50)
    assert len(started) == 2
    assert len(finished) == 1
    rw.commit_text_overlay()
    assert len(started) == 2
    assert len(finished) == 2
    assert rw.tool_mgr.active_text_editor is None


def test_render_widget_active_color_and_brush_color_reaching_shapes(app):
    """active_color é lido/escrito direto; a cor das formas chega pelo estado.

    Cadeia: BrushState.colorChanged → ShapeColorLink (ToolState "shapes") →
    CanvasToolBinding → ShapeToolController. Até 2026-09-24 havia também um
    `RenderWidget.set_shape_color` paralelo, que zerava a transparência do fundo.
    """
    from plugins.system.workspace_core.workspace.canvas_tool_binding import CanvasToolBinding
    from ui.core.plugins.registry import ServiceRegistry
    from ui.core.state import install_app_state

    rw = RenderWidget()
    assert rw.active_color == QtGui.QColor(0, 0, 0, 255)

    test_color = QtGui.QColor(12, 34, 56, 255)
    rw.active_color = test_color
    assert rw.active_color == test_color

    state = install_app_state(ServiceRegistry(), lambda: None)
    binding = CanvasToolBinding(state.tools, rw, lambda _msg: None)  # noqa: F841
    state.brush.set_color(test_color)
    assert rw.shape_ctrl.settings["stroke_color"] == test_color
    assert rw.shape_ctrl.settings["fill_color"] == test_color


def test_document_owns_paper_and_canvas_reads_it(app, monkeypatch):
    """O papel mora no Document; o canvas lê do documento ativo (sem cópia própria)."""
    from ui.core.document.document import Document
    from ui.core.document.manager import DocumentManager
    doc = Document("paper-doc", "Papel", 8, 8)
    monkeypatch.setattr(DocumentManager.instance(), "active_document", lambda: doc)
    rw = RenderWidget()
    changes = []
    doc.paper_changed.connect(lambda changed: changes.append(set(changed)))
    paper_col = QtGui.QColor(240, 230, 210)

    doc.set_paper(visible=False, color=paper_col)
    assert changes == [{"visible", "color"}]
    assert doc.is_dirty and doc.dirty_reason == "paper"
    assert rw.paper_visible is False
    assert rw.paper_color == paper_col

    doc.set_paper(color=paper_col)  # valor igual não emite
    assert len(changes) == 1
    with pytest.raises(ValueError):
        doc.set_paper(cor=paper_col)


def test_paper_layer_widget_is_a_view_of_the_document(app):
    """O widget de papel edita pelo documento e se atualiza pelo sinal dele."""
    from plugins.ui.layers_plugin.paper import PaperLayerWidget
    from ui.core.document.document import Document
    doc = Document("paper-view", "Papel", 8, 8)
    widget = PaperLayerWidget()
    widget.show_document(doc)

    widget._toggle_visibility()
    assert doc.paper_visible is False

    doc.set_paper(color=QtGui.QColor(10, 20, 30))
    assert widget.color_btn.color == QtGui.QColor(10, 20, 30)

    widget.show_document(None)
    widget._toggle_visibility()  # sem documento: nada acontece
    assert doc.paper_visible is False


def test_clear_canvas_signal_symmetry(app, monkeypatch):
    """Garante que clear_canvas emita paridade de strokeStarted/strokeFinished."""
    rw = RenderWidget()
    started = []
    finished = []
    rw.strokeStarted.connect(lambda: started.append(True))
    rw.strokeFinished.connect(lambda: finished.append(True))

    rw.clear_canvas()
    assert len(started) == 1
    assert len(finished) == 1
