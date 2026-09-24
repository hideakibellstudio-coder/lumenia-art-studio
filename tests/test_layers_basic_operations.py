"""
Suite de Testes Padrão Ouro — Fase 1: Operações Básicas de Camadas
Testa adição, exclusão, reordenação Drag & Drop C++, Alpha Lock, Clipping Mask e Merge Down.
"""

import os
import sys
import unittest

# Força execução em modo headless / offscreen para evitar janelas de UI
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Garante que a raiz do projeto Lumenia esteja no PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from ui.boundary.orchestrator.main_window import MainWindow
from ui.core.engine.registry import EngineRegistry


class TestPhase1Layers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.main_window_fixture import main_window_com_workspace
        cls.mw = main_window_com_workspace()
        cls.mw.show()
        cls.doc = cls.mw.dm.new_document(800, 600, "Doc Teste Phase 1")

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.doc = self.mw.dm.new_document(800, 600, "Doc Teste Phase 1")
        self.mw.dm.set_active_document(self.doc.uid)
        self.panel = self.mw.workspace._layers_panel
        self.panel.set_layer_manager(self.doc.layer_manager)
        self.backend = EngineRegistry.instance().get_backend()
        if self.backend:
            self.backend.set_active_document_context(self.doc.uid, 800, 600)
        self.facade = self.backend._facade

    def assert_engine_matches_document(self):
        """Documento (LocalLayerManager) e motor: mesma ordem e mesma camada ativa."""
        manager = self.panel.layer_manager
        names = [layer.name for layer in manager.layers]
        native = [self.facade.get_layer_info(i)["name"] for i in range(self.facade.get_drawing_layer_count())]
        self.assertEqual(names, native)
        self.assertEqual(manager.active_index, self.backend.get_active_layer_index())

    def tearDown(self):
        if hasattr(self, "doc") and self.doc:
            self.mw.dm.close_document(self.doc.uid)

    def test_01_layer_creation_and_deletion(self):
        """Testa adição e remoção de camadas sincronizada com C++."""
        initial_py_count = len(self.panel.layer_manager.layers)
        initial_cpp_count = self.facade.get_drawing_layer_count()
        self.assertEqual(initial_py_count, initial_cpp_count)

        # Adiciona camada
        self.panel.add_layer("Camada Teste 1")
        self.assertEqual(len(self.panel.layer_manager.layers), initial_py_count + 1)
        self.assertEqual(self.facade.get_drawing_layer_count(), initial_cpp_count + 1)

        self.assert_engine_matches_document()

        # Deleta camada (pelo painel: um único caminho até o motor)
        self.panel.delete_selection()
        self.assertEqual(len(self.panel.layer_manager.layers), initial_py_count)
        self.assertEqual(self.facade.get_drawing_layer_count(), initial_cpp_count)
        self.assert_engine_matches_document()

    def test_02_alpha_lock_and_clipping_mask(self):
        """Testa alteração de Alpha Lock e Clipping Mask no C++."""
        self.panel.add_layer("Camada Alpha")
        active = self.panel.layer_manager.get_active_layer()

        c_idx = self.panel.layer_manager.layers.index(active)

        # Alpha Lock (botão da grade)
        self.panel.grid_toggle_alpha()
        self.assertTrue(active.alpha_locked)
        self.assertTrue(self.facade.is_layer_alpha_locked(c_idx))

        # Clipping Mask (ícone do item na árvore)
        self.panel.delegate.actionRequested.emit("toggle_clipping_mask", active.uid)
        self.assertTrue(active.clipping_mask)
        self.assertTrue(self.facade.is_layer_clipping_mask(c_idx))

    def test_03_reorder_layers_cpp_sync(self):
        """Testa a reordenação em tempo real sincronizando vetor C++."""
        self.panel.add_layer("Camada A")
        self.panel.add_layer("Camada B")
        self.panel.add_layer("Camada C")

        py_names_before = [l.name for l in self.panel.layer_manager.layers]
        cpp_names_before = [self.facade.get_layer_info(i)["name"] for i in range(self.facade.get_drawing_layer_count())]
        self.assertEqual(py_names_before, cpp_names_before)

        # Reordena pelo documento (o caminho do arrastar-e-soltar). A ordem e a
        # camada ativa chegam ao motor sem o painel fazer nada.
        new_uids = [l.uid for l in reversed(self.panel.layer_manager.layers)]
        parent_map = {str(l.uid): l.parent_uid for l in self.panel.layer_manager.layers}
        self.panel.layer_manager.reorder_and_reparent([str(u) for u in new_uids], parent_map)
        self.assert_engine_matches_document()

        # Mover pelo painel também mantém os dois lados iguais.
        self.panel.move_down()
        self.assert_engine_matches_document()
        self.panel.move_up()
        self.assert_engine_matches_document()

    def test_04_merge_layer_down(self):
        """Testa a mesclagem de camadas para baixo C++."""
        self.panel.add_layer("Camada Base")
        self.panel.add_layer("Camada Topo")
        count_before = len(self.panel.layer_manager.layers)

        self.panel.merge_down()
        count_after = len(self.panel.layer_manager.layers)
        self.assertEqual(count_after, count_before - 1)
        self.assertEqual(self.facade.get_drawing_layer_count(), count_after)
        self.assert_engine_matches_document()

    def test_05_duplicate_layer_cpp_sync(self):
        """Testa a duplicação de camadas sincronizando vetor nativo C++."""
        self.panel.add_layer("Camada Original")
        py_count_before = len(self.panel.layer_manager.layers)
        cpp_count_before = self.facade.get_drawing_layer_count()

        self.panel.duplicate_layer()

        py_count_after = len(self.panel.layer_manager.layers)
        cpp_count_after = self.facade.get_drawing_layer_count()

        self.assertEqual(py_count_after, py_count_before + 1)
        self.assertEqual(cpp_count_after, cpp_count_before + 1)

        self.assert_engine_matches_document()

    def test_06_filter_layer_is_created_by_the_document(self):
        """Camada de ajuste nasce no documento e no motor de uma vez, já marcada como filtro."""
        manager = self.panel.layer_manager
        uid = manager.add_filter_layer("Ajuste Teste", 1, [0.5, 0.5, 0.5, 0.5])
        layer = manager.get_layer_by_uid(uid)
        idx = manager.layers.index(layer)
        self.assertTrue(layer.is_filter)
        self.assertTrue(self.backend.is_filter_layer(idx))
        self.assertEqual(self.backend.get_filter_type(idx), 1)
        self.assert_engine_matches_document()


if __name__ == "__main__":
    unittest.main()
