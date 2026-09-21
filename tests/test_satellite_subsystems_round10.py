"""
Testes de Integridade dos Subsistemas Satélites — Rodada 10 (ARCcC v2)
=====================================================================
Validações de:
- Cor do Balde de Tinta (do_flood_fill) e garantia de simetria de sinais via try/finally.
- Simetria de ciclo de vida do TextToolController (strokeStarted/strokeFinished).
- active_color e set_shape_color no RenderWidget e CanvasCompatMixin.
- Método canônico set_paper_state no RenderWidget e sinal paperChanged em PaperLayerWidget.
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


def test_render_widget_active_color_and_set_shape_color(app):
    """Garante leitura/escrita de active_color e propagação para set_shape_color."""
    rw = RenderWidget()
    assert rw.active_color == QtGui.QColor(0, 0, 0, 255)

    test_color = QtGui.QColor(12, 34, 56, 255)
    rw.active_color = test_color
    assert rw.active_color == test_color

    # Testa propagação via set_shape_color
    rw.set_shape_color(test_color)
    assert rw.shape_ctrl.settings["stroke_color"] == test_color
    assert rw.shape_ctrl.settings["fill_color"] == test_color


def test_render_widget_set_paper_state_canonical(app):
    """Garante funcionamento do método canônico set_paper_state no RenderWidget."""
    rw = RenderWidget()
    paper_col = QtGui.QColor(240, 230, 210)
    rw.set_paper_state(False, paper_col)

    assert rw.paper_visible is False
    assert rw.paper_color == paper_col

    rw.set_paper_state(True)
    assert rw.paper_visible is True
    assert rw.paper_color == paper_col


def test_paper_layer_widget_emits_paper_changed(app):
    """Garante emissão do sinal paperChanged no PaperLayerWidget."""
    from plugins.ui.layers_plugin.paper import PaperLayerWidget
    widget = PaperLayerWidget()
    emitted = []
    widget.paperChanged.connect(lambda vis, col: emitted.append((vis, col)))

    widget._toggle_visibility()
    assert len(emitted) == 1
    assert emitted[0][0] is False


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
