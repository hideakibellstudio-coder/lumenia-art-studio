import unittest
from PySide6 import QtWidgets

from ui.core.document.layer_manager import LocalLayerManager

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["--platform", "offscreen"])


class TestLayerManagerStructuralHistory(unittest.TestCase):
    def test_rename_and_reorder_restore_stable_uids(self):
        manager = LocalLayerManager()
        first = manager.add_layer("A")
        second = manager.add_layer("B")
        before = manager._snapshot()
        manager.rename_layer(first, "A2")
        manager.move_layer_down(second)
        manager._restore_snapshot(before)
        self.assertEqual([layer.uid for layer in manager.layers], [first, second])
        self.assertEqual(manager.get_layer_by_uid(first).name, "A")


if __name__ == "__main__":
    unittest.main()
