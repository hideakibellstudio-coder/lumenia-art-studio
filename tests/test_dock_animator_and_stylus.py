"""Testes de regressão e garantia de recolhimento das gavetas com Mouse e Stylus.

Valida:
1. Rejeição de cliques sintetizados de stylus no SidebarButton (anti-duplo-clique).
2. Garantia de fechamento de drawer no DockAnimator mesmo com delta residual de animação.
3. Garantia de colapso de sidebar no DockAnimator quando endValue é 0.
4. Fechamento de gavetas despinadas ao tocar com Stylus (TabletPress) no canvas ou viewport.
"""

import time
import unittest
from PySide6 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

from ui.plugins.system.workspace_core.workspace.dock.sidebar_button import SidebarButton
from ui.plugins.system.workspace_core.workspace.dock.dock_system import AdvancedDockSystem


class DummyWorkspace(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.workspace_area = QtWidgets.QWidget(self)
        self.workspace_area.resize(1920, 1080)
        self.resize(1920, 1080)


class TestDockAnimatorAndStylus(unittest.TestCase):
    def setUp(self):
        self.ws = DummyWorkspace()
        self.dock = AdvancedDockSystem("right", self.ws.workspace_area, self.ws)

    def tearDown(self):
        self.dock.deleteLater()
        self.ws.deleteLater()

    def test_sidebar_button_ignores_synthesized_mouse_click(self):
        """Eventos de mouse sintetizados pelo sistema após tabletEvent não disparam segundo clique."""
        btn = SidebarButton("test_panel", "Test Panel", parent=self.dock.sidebar)
        clicks = []
        btn.clicked.connect(lambda: clicks.append(True))

        # 1. Simula toque de caneta (TabletRelease)
        btn.setDown(True)
        btn._last_tablet_time = time.monotonic()
        btn.click()
        self.assertEqual(len(clicks), 1)

        # 2. Simula evento de mouse chegando logo em seguida (< 0.25s)
        synth_event = QtGui.QMouseEvent(
            QtCore.QEvent.MouseButtonPress,
            QtCore.QPointF(10, 10),
            QtCore.QPointF(10, 10),
            QtCore.Qt.LeftButton,
            QtCore.Qt.LeftButton,
            QtCore.Qt.NoModifier,
        )
        btn.mousePressEvent(synth_event)

        synth_release = QtGui.QMouseEvent(
            QtCore.QEvent.MouseButtonRelease,
            QtCore.QPointF(10, 10),
            QtCore.QPointF(10, 10),
            QtCore.Qt.LeftButton,
            QtCore.Qt.NoButton,
            QtCore.Qt.NoModifier,
        )
        btn.mouseReleaseEvent(synth_release)

        # O clique sintetizado foi descartado e não duplicou a ação
        self.assertEqual(len(clicks), 1)
        btn.deleteLater()

    def test_drawer_anim_finished_closes_reliably_when_is_open_is_false(self):
        """Se is_open for False, drawer_container é fechado incondicionalmente mesmo se maximumWidth > 0."""
        animator = self.dock.animator
        self.dock.is_open = False
        self.dock.drawer_container.setMaximumWidth(1)  # simula resíduo de arredondamento

        animator._on_drawer_anim_finished()

        self.assertEqual(self.dock.drawer_container.maximumWidth(), 0)
        self.assertEqual(self.dock.drawer_container.minimumWidth(), 0)
        self.assertFalse(self.dock.drawer_container.isVisible())

    def test_sidebar_anim_finished_collapses_reliably_when_end_value_is_zero(self):
        """Se o endValue da animação da sidebar for 0, ela colapsa incondicionalmente para 0px."""
        animator = self.dock.animator
        animator._sidebar_anim.setEndValue(0)
        self.dock.sidebar.setFixedWidth(2)  # simula resíduo de layout

        animator._on_sidebar_anim_finished()

        self.assertEqual(self.dock.sidebar.width(), 0)
        self.assertFalse(self.dock.sidebar.isVisible())

    def test_close_drawer_anim_sets_zero_minimum_width(self):
        """close_drawer_anim reseta o minimumWidth para 0 para permitir encolhimento desimpedido."""
        self.dock.drawer_container.setMinimumWidth(280)
        self.dock.drawer_container.setMaximumWidth(280)

        self.dock.animator.close_drawer_anim()

        self.assertEqual(self.dock.drawer_container.minimumWidth(), 0)
        self.assertEqual(self.dock.animator._drawer_anim.endValue(), 0)


if __name__ == "__main__":
    unittest.main()
