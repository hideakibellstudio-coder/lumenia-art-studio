"""Comprehensive unit tests for Camada 3 - Fase 5: BrushTextureIO.

Tests decoupled texture IO and workspace application under ARCcC v2.
"""

import unittest
from unittest.mock import MagicMock, patch
from PySide6 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

from plugins.system.workspace_core.workspace.brush_texture_io import BrushTextureIO


class TestBrushTextureIO(unittest.TestCase):
    """Verifies BrushTextureIO file handling and workspace dispatch."""

    @patch("PySide6.QtWidgets.QFileDialog.getOpenFileName", return_value=("", ""))
    def test_prompt_and_load_texture_cancelled(self, mock_dialog):
        """Returns None when user cancels the file dialog."""
        result = BrushTextureIO.prompt_and_load_texture()
        self.assertIsNone(result)

    @patch("PySide6.QtWidgets.QFileDialog.getOpenFileName")
    @patch("PySide6.QtWidgets.QMessageBox.warning")
    def test_prompt_and_load_texture_invalid_file(self, mock_warning, mock_dialog):
        """Handles non-existent or invalid image files safely."""
        mock_dialog.return_value = ("non_existent_file.png", "")
        result = BrushTextureIO.prompt_and_load_texture()
        self.assertIsNone(result)
        mock_warning.assert_called_once()

    @patch.object(BrushTextureIO, "prompt_and_load_texture")
    def test_load_and_apply_to_workspace_dispatches_correctly(self, mock_prompt):
        """Applies loaded texture to renderer, backend, and dock."""
        dummy_bytes = b"\x00\x01\x02\x03" * 16
        mock_prompt.return_value = (dummy_bytes, 4, 4, "/path/to/texture.png")

        workspace = MagicMock()
        renderer = MagicMock()
        workspace.canvas_widget.renderer = renderer
        dock = MagicMock()
        workspace._brush_dock = dock

        # Test shape texture
        success = BrushTextureIO.load_and_apply_to_workspace(workspace, is_shape=True)
        self.assertTrue(success)
        renderer.set_shape_texture.assert_called_once_with(dummy_bytes, 4, 4)
        dock.update_thumbnail.assert_called_once_with(True, "/path/to/texture.png")
        workspace.canvas_widget.update.assert_called_once()

        # Reset mocks
        renderer.reset_mock()
        dock.reset_mock()
        workspace.canvas_widget.update.reset_mock()

        # Test heightmap texture
        success_hm = BrushTextureIO.load_and_apply_to_workspace(workspace, is_shape=False)
        self.assertTrue(success_hm)
        renderer.set_heightmap_texture.assert_called_once_with(dummy_bytes, 4, 4)
        dock.update_thumbnail.assert_called_once_with(False, "/path/to/texture.png")


if __name__ == "__main__":
    unittest.main()
