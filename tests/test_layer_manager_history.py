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

    def test_layer_0_never_clipping_mask_after_move_layer_up(self):
        manager = LocalLayerManager()
        first = manager.add_layer("A")
        second = manager.add_layer("B")
        manager.set_clipping_mask(1, True)
        self.assertTrue(manager.layers[1].clipping_mask)

        # Subir a primeira camada empurra a segunda (que era máscara) para o índice 0
        manager.move_layer_up(first)
        self.assertEqual(manager.layers[0].uid, second)
        self.assertFalse(manager.layers[0].clipping_mask)

    def test_layer_0_never_clipping_mask_after_reorder_and_reparent(self):
        manager = LocalLayerManager()
        first = manager.add_layer("A")
        second = manager.add_layer("B")
        manager.set_clipping_mask(1, True)
        self.assertTrue(manager.layers[1].clipping_mask)

        # Arrastar e soltar reordenando para [B, A]
        manager.reorder_and_reparent([second, first], {})
        self.assertEqual(manager.layers[0].uid, second)
        self.assertFalse(manager.layers[0].clipping_mask)

    def test_layer_0_never_clipping_mask_after_replace_layers(self):
        manager = LocalLayerManager()
        records = [
            {"uid": 10, "name": "Bottom", "clipping_mask": True},
            {"uid": 20, "name": "Top", "clipping_mask": False},
        ]
        manager.replace_layers(records)
        self.assertEqual(manager.layers[0].uid, 10)
        self.assertFalse(manager.layers[0].clipping_mask)


if __name__ == "__main__":
    unittest.main()
