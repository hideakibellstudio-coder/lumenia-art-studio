"""
Suite de Testes Padrão Ouro — Fase 2: Grupos de Camadas e Estrutura Hierárquica
Testa criação de grupos, aninhamento de sub-grupos, modo Atravessar (Pass-Through) e opacidade/visibilidade efetiva recursivas.
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
from ui.core.document.layer_blend_mode import LayerBlendMode


class TestPhase2Groups(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ui.boundary.orchestrator.main_window import MainWindow
        top_mws = [w for w in QApplication.topLevelWidgets() if isinstance(w, MainWindow)]
        if top_mws:
            cls.mw = top_mws[0]
        else:
            cls.mw = MainWindow()
            cls.mw.show()
        cls.doc = cls.mw.dm.new_document(800, 600, "Doc Teste Phase 2")

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.mw.dm.set_active_document(self.doc.uid)
        self.panel = self.mw.workspace._layers_panel
        self.backend = EngineRegistry.instance().get_backend()
        if self.backend and (self.backend._facade is None):
            self.backend.set_active_document_context(self.doc.uid, 800, 600)
        self.facade = self.backend._facade

        # Limpa o vetor C++ e o gerenciador Python mantendo uma Camada 1 base
        while self.facade.get_drawing_layer_count() > 1:
            self.facade.remove_layer(self.facade.get_drawing_layer_count() - 1)
        self.facade.set_layer_name(0, "Camada 1")

        self.panel.layer_manager.layers.clear()
        self.panel.layer_manager._next_uid = 1
        self.panel.layer_manager._active_uid = None
        self.panel.layer_manager.add_layer("Camada 1")
        self.panel._native_uids = [l.uid for l in self.panel.layer_manager.layers]

    def test_01_default_group_pass_through(self):
        """Valida se todo novo grupo nasce com o modo Atravessar (Pass-Through)."""
        self.panel.add_group("Grupo Padrão")
        group_layer = [l for l in self.panel.layer_manager.layers if l.name == "Grupo Padrão"][0]
        self.assertTrue(group_layer.is_group)
        # blend_mode agora e' o enum canonico LayerBlendMode, nao mais o
        # rotulo cru "Atravessar" -- ver ui.core.document.layer_blend_mode.
        self.assertEqual(group_layer.blend_mode, LayerBlendMode.PASS_THROUGH)

    def test_02_nested_subgroups_and_sublayers(self):
        """Valida aninhamento hierárquico de sub-camadas e sub-grupos dentro de grupos."""
        self.panel.add_group("Pasta Raiz")
        root_group = [l for l in self.panel.layer_manager.layers if l.name == "Pasta Raiz"][0]

        # Com Pasta Raiz selecionada, adiciona sub-camada e sub-grupo
        self.panel.add_layer("Desenho Interno")
        self.panel.add_group("Sub-Pasta")

        sub_layer = [l for l in self.panel.layer_manager.layers if l.name == "Desenho Interno"][0]
        sub_group = [l for l in self.panel.layer_manager.layers if l.name == "Sub-Pasta"][0]

        self.assertEqual(sub_layer.parent_uid, root_group.uid)
        self.assertEqual(sub_group.parent_uid, root_group.uid)

    def test_03_recursive_effective_visibility(self):
        """Valida se oculta um grupo pai torna effective_visible False em todas as camadas filhas."""
        self.panel.add_group("Grupo Visibilidade")
        group = [l for l in self.panel.layer_manager.layers if l.name == "Grupo Visibilidade"][0]
        self.panel.add_layer("Filha 1")
        child = [l for l in self.panel.layer_manager.layers if l.name == "Filha 1"][0]

        self.assertTrue(self.panel.model.get_effective_visible(child))

        # Oculta grupo pai
        group.visible = False
        self.assertFalse(self.panel.model.get_effective_visible(child))

        # Reexibe grupo pai
        group.visible = True
        self.assertTrue(self.panel.model.get_effective_visible(child))

    def test_04_recursive_effective_opacity(self):
        """Valida a multiplicação recursiva de opacidade entre grupos e camadas filhas."""
        self.panel.add_group("Grupo Opacidade")
        group = [l for l in self.panel.layer_manager.layers if l.name == "Grupo Opacidade"][0]
        self.panel.add_layer("Filha Opacidade")
        child = [l for l in self.panel.layer_manager.layers if l.name == "Filha Opacidade"][0]

        group.opacity = 0.5
        child.opacity = 0.8

        eff_op = self.panel.model.get_effective_opacity(child)
        self.assertAlmostEqual(eff_op, 0.4, places=4)


if __name__ == "__main__":
    unittest.main()
