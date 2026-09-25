"""Comprehensive unit tests for Camada 3 - Fase 3: Dock System Decomposition.

Tests DockGeometryCalculator, DockStateStore, DockAnimator,
and AdvancedDockSystem integration under ARCcC v2.
"""

import unittest
from PySide6 import QtCore, QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

from ui.plugins.system.workspace_core.workspace.dock.dock_geometry_calculator import (
    DockGeometryCalculator
)
from ui.plugins.system.workspace_core.workspace.dock.dock_state_store import (
    DockStateStore
)
from ui.plugins.system.workspace_core.workspace.dock.dock_animator import (
    DockAnimator,
    SPEED_MAP,
    DELAY_MAP
)
from ui.plugins.system.workspace_core.workspace.dock.dock_system import AdvancedDockSystem


class DummyWorkspace(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.workspace_area = QtWidgets.QWidget(self)
        self.workspace_area.resize(1920, 1080)
        self.resize(1920, 1080)


class TestDockGeometryCalculator(unittest.TestCase):
    """Verifies geometry and unpinned dock placement calculations."""

    def test_unpinned_geometry_left(self):
        """Left dock unpinned drawer sits immediately after 54px sidebar."""
        geo = DockGeometryCalculator.compute_unpinned_geometry("left", 1920, 1080, 280)
        self.assertEqual(geo.x(), 54)
        self.assertEqual(geo.y(), 0)
        self.assertEqual(geo.width(), 280)
        self.assertEqual(geo.height(), 1080)

    def test_unpinned_geometry_right(self):
        """Right dock unpinned drawer sits to the left of the 54px sidebar slot."""
        geo = DockGeometryCalculator.compute_unpinned_geometry("right", 1920, 1080, 280)
        expected_x = 1920 - 54 - 280
        self.assertEqual(geo.x(), expected_x)
        self.assertEqual(geo.y(), 0)
        self.assertEqual(geo.width(), 280)
        self.assertEqual(geo.height(), 1080)


class TestDockStateStore(unittest.TestCase):
    """Verifies dock state serialization and restoration."""

    def test_serialize_state(self):
        """Serializes dock configuration to dictionary."""
        data = DockStateStore.serialize_state(
            is_open=True,
            is_pinned=False,
            active_panel_ids={"layers", "brush"},
            drawer_width=280,
            panel_order=["brush", "layers", "color"]
        )
        self.assertTrue(data["is_open"])
        self.assertFalse(data["is_pinned"])
        self.assertIn("layers", data["active_panel_ids"])
        self.assertIn("brush", data["active_panel_ids"])
        self.assertEqual(data["width"], 280)
        self.assertEqual(data["panel_order"], ["brush", "layers", "color"])


class TestAdvancedDockSystemIntegration(unittest.TestCase):
    """Verifies AdvancedDockSystem lifecycle, panels, and delegation."""

    def setUp(self):
        self.ws = DummyWorkspace()
        self.dock = AdvancedDockSystem("right", self.ws.workspace_area, self.ws)

    def tearDown(self):
        self.dock.deleteLater()
        self.ws.deleteLater()

    def test_initial_state(self):
        """Dock initializes with expected defaults."""
        self.assertFalse(self.dock.is_open)
        self.assertFalse(self.dock.is_pinned)
        self.assertEqual(self.dock.side, "right")
        self.assertIsInstance(self.dock.animator, DockAnimator)

    def test_add_and_toggle_panel(self):
        """Adding a panel and toggling opens drawer."""
        p_widget = QtWidgets.QWidget()
        self.dock.add_panel("test_panel", "Test Panel", p_widget)

        opened_signal = []
        self.dock.drawer_opened.connect(lambda pid: opened_signal.append(pid))

        self.dock.toggle_panel("test_panel")
        self.assertTrue(self.dock.is_open)
        self.assertIn("test_panel", self.dock.active_panel_ids)
        self.assertEqual(len(opened_signal), 1)
        self.assertEqual(opened_signal[0], "test_panel")

        # Toggling again closes drawer
        closed_signal = []
        self.dock.drawer_closed.connect(lambda: closed_signal.append(True))
        self.dock.toggle_panel("test_panel")
        self.assertFalse(self.dock.is_open)
        self.assertNotIn("test_panel", self.dock.active_panel_ids)
        self.assertEqual(len(closed_signal), 1)

    def test_state_persistence_roundtrip(self):
        """Saving and restoring state restores open panel and pin state."""
        p_widget = QtWidgets.QWidget()
        self.dock.add_panel("layers", "Camadas", p_widget)
        self.dock.toggle_panel("layers")
        self.dock.set_pinned(True)

        state = self.dock.get_state()
        self.assertTrue(state["is_open"])
        self.assertTrue(state["is_pinned"])
        self.assertIn("layers", state["active_panel_ids"])

        # Reset dock
        self.dock.close_drawer()
        self.dock.set_pinned(False)
        self.assertFalse(self.dock.is_open)
        self.assertFalse(self.dock.is_pinned)

        # Restore
        self.dock.restore_state(state)
        self.assertTrue(self.dock.is_pinned)
        self.assertTrue(self.dock.is_open)
        self.assertIn("layers", self.dock.active_panel_ids)


if __name__ == "__main__":
    unittest.main()
