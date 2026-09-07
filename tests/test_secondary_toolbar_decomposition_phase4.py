"""Comprehensive unit tests for Camada 3 - Fase 4: SecondaryToolBar Decomposition.

Tests composed SecondaryToolbarHandlersMixin and domain-specific mixins under ARCcC v2.
"""

import unittest
from PySide6 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

from plugins.system.workspace_core.workspace.secondary_tool_bar.toolbar import SecondaryToolBar
from plugins.system.workspace_core.workspace.secondary_tool_bar.toolbar_handlers import (
    SecondaryToolbarHandlersMixin
)
from plugins.system.workspace_core.workspace.secondary_tool_bar.handlers.selection_toolbar_handlers import (
    SelectionToolbarHandlersMixin
)
from plugins.system.workspace_core.workspace.secondary_tool_bar.handlers.shape_text_toolbar_handlers import (
    ShapeTextToolbarHandlersMixin
)
from plugins.system.workspace_core.workspace.secondary_tool_bar.handlers.brush_fill_toolbar_handlers import (
    BrushFillToolbarHandlersMixin
)


class TestSecondaryToolbarDecomposition(unittest.TestCase):
    """Verifies domain mixins composition and handlers functionality."""

    def setUp(self):
        self.toolbar = SecondaryToolBar()

    def tearDown(self):
        self.toolbar.deleteLater()

    def test_inheritance_and_method_presence(self):
        """SecondaryToolBar inherits all 3 specialized handler mixins."""
        self.assertTrue(issubclass(SecondaryToolbarHandlersMixin, SelectionToolbarHandlersMixin))
        self.assertTrue(issubclass(SecondaryToolbarHandlersMixin, ShapeTextToolbarHandlersMixin))
        self.assertTrue(issubclass(SecondaryToolbarHandlersMixin, BrushFillToolbarHandlersMixin))

        expected_methods = [
            "_on_wand_tol_changed", "_on_geom_feather_changed", "_on_lasso_feather_changed",
            "_on_shape_type_changed", "_on_shape_stroke_changed", "_on_text_size_changed",
            "_on_smudge_stretch_changed", "_on_bucket_tol_changed", "_on_trans_interp_changed"
        ]
        for m in expected_methods:
            self.assertTrue(hasattr(self.toolbar, m), f"Method {m} must be present on SecondaryToolBar")

    def test_selection_handlers_dispatch(self):
        """Selection handler updates values and emits settingsChanged signal."""
        emitted = []
        self.toolbar.settingsChanged.connect(lambda tool, s: emitted.append((tool, s)))

        self.toolbar._on_wand_tol_changed(45, "h")
        self.assertEqual(self.toolbar.lbl_wand_tol_val_h.text(), "45%")
        self.assertEqual(self.toolbar._settings_cache["wand"]["tolerance"], 45)
        self.assertTrue(any(e[0] == "wand" for e in emitted))

    def test_shape_and_text_handlers_dispatch(self):
        """Shape and text handlers update settings cache and emit signal."""
        emitted = []
        self.toolbar.settingsChanged.connect(lambda tool, s: emitted.append((tool, s)))

        self.toolbar._on_shape_stroke_changed(12, "h")
        self.assertEqual(self.toolbar.lbl_shape_stroke_val_h.text(), "12px")
        self.assertEqual(self.toolbar._settings_cache["shapes"]["stroke_width"], 12)

        self.toolbar._on_text_size_changed(48, "h")
        self.assertEqual(self.toolbar._settings_cache["text"]["font_size"], 48)

    def test_brush_and_transform_handlers_dispatch(self):
        """Smudge, bucket, and transform handlers update settings correctly."""
        emitted = []
        self.toolbar.settingsChanged.connect(lambda tool, s: emitted.append((tool, s)))

        self.toolbar._on_smudge_stretch_changed(65, "h")
        self.assertEqual(self.toolbar.lbl_smudge_stretch_val_h.text(), "65%")
        self.assertEqual(self.toolbar._settings_cache["smudge"]["smudge_stretch"], 0.65)

        self.toolbar._on_bucket_tol_changed(30, "h")
        self.assertEqual(self.toolbar.lbl_bkt_tol_val_h.text(), "30%")
        self.assertEqual(self.toolbar._settings_cache["bucket"]["tolerance"], 30)


if __name__ == "__main__":
    unittest.main()
