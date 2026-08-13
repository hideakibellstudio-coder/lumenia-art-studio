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
        cls.mw = MainWindow()
        cls.mw.show()
        cls.mw.dm.new_document(800, 600, "Doc Teste Phase 1")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "mw") and cls.mw:
            cls.mw.close()

    def setUp(self):
        self.panel = self.mw.workspace._layers_panel
        self.backend = EngineRegistry.instance().get_backend()
        self.facade = self.backend._facade

        # Limpa totalmente o vetor C++ e o gerenciador Python e reinicializa com "Camada 1"
        while self.facade.get_drawing_layer_count() > 0:
            self.facade.remove_layer(0)
        self.facade.add_layer("Camada 1")

        self.panel.layer_manager.layers.clear()
        self.panel.layer_manager._next_uid = 1
        self.panel.layer_manager._active_uid = None
        self.panel.layer_manager.add_layer("Camada 1")
        self.panel._native_uids = [l.uid for l in self.panel.layer_manager.layers]

    def test_01_layer_creation_and_deletion(self):
        """Testa adição e remoção de camadas sincronizada com C++."""
        initial_py_count = len(self.panel.layer_manager.layers)
        initial_cpp_count = self.facade.get_drawing_layer_count()
        self.assertEqual(initial_py_count, initial_cpp_count)

        # Adiciona camada
        self.panel.add_layer("Camada Teste 1")
        self.assertEqual(len(self.panel.layer_manager.layers), initial_py_count + 1)
        self.assertEqual(self.facade.get_drawing_layer_count(), initial_cpp_count + 1)

        # Deleta camada
        active = self.panel.layer_manager.get_active_layer()
        self.panel.layer_manager.remove_layer(active.uid)
        self.panel._sync_to_native_engine("delete", active.uid)
        self.assertEqual(len(self.panel.layer_manager.layers), initial_py_count)
        self.assertEqual(self.facade.get_drawing_layer_count(), initial_cpp_count)

    def test_02_alpha_lock_and_clipping_mask(self):
        """Testa alteração de Alpha Lock e Clipping Mask no C++."""
        self.panel.add_layer("Camada Alpha")
        active = self.panel.layer_manager.get_active_layer()

        # Alpha Lock
        active.alpha_locked = True
        self.panel._sync_to_native_engine("alpha_lock", active.uid, True)
        self.assertTrue(active.alpha_locked)
        c_idx = self.panel.layer_manager.layers.index(active)
        self.assertTrue(self.facade.is_layer_alpha_locked(c_idx))

        # Clipping Mask
        active.clipping_mask = True
        self.panel._sync_to_native_engine("clipping_mask", active.uid, True)
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

        # Reordena no Python (inverte ordem)
        new_uids = [l.uid for l in reversed(self.panel.layer_manager.layers)]
        parent_map = {str(l.uid): l.parent_uid for l in self.panel.layer_manager.layers}
        self.panel.layer_manager.reorder_and_reparent([str(u) for u in new_uids], parent_map)
        self.panel._sync_to_native_engine("reorder_all")

        py_names_after = [l.name for l in self.panel.layer_manager.layers]
        cpp_names_after = [self.facade.get_layer_info(i)["name"] for i in range(self.facade.get_drawing_layer_count())]
        self.assertEqual(py_names_after, cpp_names_after)

    def test_04_merge_layer_down(self):
        """Testa a mesclagem de camadas para baixo C++."""
        self.panel.add_layer("Camada Base")
        self.panel.add_layer("Camada Topo")
        count_before = len(self.panel.layer_manager.layers)

        self.panel.merge_down()
        count_after = len(self.panel.layer_manager.layers)
        self.assertEqual(count_after, count_before - 1)
        self.assertEqual(self.facade.get_drawing_layer_count(), count_after)

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

        py_names = [l.name for l in self.panel.layer_manager.layers]
        cpp_names = [self.facade.get_layer_info(i)["name"] for i in range(self.facade.get_drawing_layer_count())]
        self.assertEqual(py_names, cpp_names)


if __name__ == "__main__":
    unittest.main()
