"""Test MDI Multi-Document Lifecycle & C++ Facade Isolation."""

import unittest

from PySide6 import QtGui, QtWidgets

# Assegura que QApplication existe em modo offscreen
app = QtWidgets.QApplication.instance()
if app is None:
    app = QtWidgets.QApplication(["--platform", "offscreen"])

from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry


class TestMdiMultiDocLifecycle(unittest.TestCase):
    """Suíte de testes de ciclo de vida MDI, abas e isolamento C++ por documento."""

    @classmethod
    def setUpClass(cls):
        from tests.main_window_fixture import main_window_com_workspace
        cls.win = main_window_com_workspace()
        cls.backend = EngineRegistry.instance().get_backend()

    def setUp(self):
        self.dm = DocumentManager.instance()
        # Fecha todos os documentos remanescentes
        for uid in list(self.dm._documents.keys()):
            self.dm.close_document(uid)

    def test_01_create_multiple_documents_with_isolated_facades(self):
        """Valida que múltiplos documentos criam facades C++ distintas sem se sobrescreverem."""
        doc1 = self.dm.new_document(1920, 1080, "Documento 1")
        self.win.workspace.canvas_widget.zoom = 1.5
        self.win.workspace.canvas_widget.pan_x = 50.0

        # Desenha na camada do Doc 1
        if self.backend and hasattr(self.backend, "_facade") and self.backend._facade:
            self.assertEqual(self.backend._facade.get_width(), 1920)
            self.assertEqual(self.backend._facade.get_height(), 1080)
            self.backend.start_stroke(100.0, 100.0, 1.0)
            self.backend.paint_stroke(150.0, 150.0, 1.0)
            self.backend.end_stroke()

        # Cria Doc 2 com resolução diferente
        doc2 = self.dm.new_document(800, 600, "Documento 2")
        self.win.workspace.canvas_widget.zoom = 2.0
        self.win.workspace.canvas_widget.pan_x = -30.0

        # Verifica dimensões ativas do Doc 2
        if self.backend and hasattr(self.backend, "_facade") and self.backend._facade:
            self.assertEqual(self.backend._facade.get_width(), 800)
            self.assertEqual(self.backend._facade.get_height(), 600)

        # Alterna de volta para Doc 1
        self.dm.set_active_document(doc1.uid)
        self.assertEqual(self.dm.active_document().uid, doc1.uid)

        # Câmera e dimensões do Doc 1 devem ter sido restauradas
        self.assertEqual(self.win.workspace.canvas_widget.zoom, 1.5)
        self.assertEqual(self.win.workspace.canvas_widget.pan_x, 50.0)
        if self.backend and hasattr(self.backend, "_facade") and self.backend._facade:
            self.assertEqual(self.backend._facade.get_width(), 1920)
            self.assertEqual(self.backend._facade.get_height(), 1080)

        # Alterna para Doc 2
        self.dm.set_active_document(doc2.uid)
        self.assertEqual(self.win.workspace.canvas_widget.zoom, 2.0)
        self.assertEqual(self.win.workspace.canvas_widget.pan_x, -30.0)
        if self.backend and hasattr(self.backend, "_facade") and self.backend._facade:
            self.assertEqual(self.backend._facade.get_width(), 800)
            self.assertEqual(self.backend._facade.get_height(), 600)

    def test_02_paper_and_flood_isolation(self):
        """Valida que papel e camadas de preenchimento são isoladas por documento."""
        # O papel é de cada documento (Document.set_paper); o canvas só o mostra.
        doc1 = self.dm.new_document(1000, 1000, "Doc A", bg_color=(255, 0, 0, 255))
        doc2 = self.dm.new_document(500, 500, "Doc B", bg_color=(0, 0, 255, 255))
        doc2.set_paper(color=QtGui.QColor(0, 255, 0))

        # Volta para Doc 1
        self.dm.set_active_document(doc1.uid)
        self.assertEqual(self.win.workspace.canvas_widget.paper_color, QtGui.QColor(255, 0, 0))

        # Volta para Doc 2
        self.dm.set_active_document(doc2.uid)
        self.assertEqual(self.win.workspace.canvas_widget.paper_color, QtGui.QColor(0, 255, 0))

    def test_03_close_document_cleans_up_memory(self):
        """Valida fechamento de abas e desalocação no motor nativo."""
        doc1 = self.dm.new_document(400, 400, "Fechar 1")
        doc2 = self.dm.new_document(400, 400, "Fechar 2")

        if self.backend and hasattr(self.backend, "_doc_facades"):
            self.assertIn(doc1.uid, self.backend._doc_facades)
            self.assertIn(doc2.uid, self.backend._doc_facades)

        # Fecha Doc 1
        self.dm.close_document(doc1.uid)
        if self.backend and hasattr(self.backend, "_doc_facades"):
            self.assertNotIn(doc1.uid, self.backend._doc_facades)

        # Fecha Doc 2
        self.dm.close_document(doc2.uid)
        self.assertIsNone(self.dm.active_document())
        self.assertFalse(self.win.workspace.canvas_widget.isEnabled())


if __name__ == "__main__":
    unittest.main()
