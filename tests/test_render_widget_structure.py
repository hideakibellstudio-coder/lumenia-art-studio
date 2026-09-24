"""Comprehensive unit tests for Camada 3 - Fase 2: RenderWidget Decomposition.

Tests ToolManager, CanvasBackgroundRenderer, CanvasStrokePipeline,
and RenderWidget backward-compatible delegations.
"""

import unittest
from PySide6 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
from plugins.system.workspace_core.workspace.canvas.tools.tool_manager import ToolManager
from plugins.system.workspace_core.workspace.canvas.renderers.canvas_background_renderer import (
    CanvasBackgroundRenderer
)
from plugins.system.workspace_core.workspace.canvas.viewport.canvas_stroke_pipeline import (
    CanvasStrokePipeline
)
from plugins.system.workspace_core.workspace.canvas.viewport.viewport_renderer import ViewportRenderer


class TestCanvasBackgroundRenderer(unittest.TestCase):
    """Verifies transparency checkerboard brush and background painting."""

    def test_checker_brush_creation(self):
        """Checker brush creates a valid QBrush with QPixmap texture."""
        brush = CanvasBackgroundRenderer.create_checker_brush()
        self.assertIsInstance(brush, QtGui.QBrush)
        self.assertFalse(brush.texture().isNull())
        self.assertEqual(brush.texture().width(), 32)
        self.assertEqual(brush.texture().height(), 32)

    def test_render_background_paper_and_checker(self):
        """Paints paper color when visible, checkerboard otherwise."""
        img = QtGui.QImage(100, 100, QtGui.QImage.Format_ARGB32_Premultiplied)
        painter = QtGui.QPainter(img)
        brush = CanvasBackgroundRenderer.create_checker_brush()

        try:
            # Paper visible: fills with paper color
            CanvasBackgroundRenderer.render_background(
                painter, QtCore.QRect(0, 0, 100, 100),
                paper_visible=True, paper_color=QtGui.QColor(255, 255, 255),
                checker_brush=brush
            )
            # Paper hidden: fills with checker brush
            CanvasBackgroundRenderer.render_background(
                painter, QtCore.QRect(0, 0, 100, 100),
                paper_visible=False, paper_color=QtGui.QColor(255, 255, 255),
                checker_brush=brush
            )
        finally:
            painter.end()


class TestToolManagerAndDelegation(unittest.TestCase):
    """Verifies ToolManager lifecycle, controllers, and RenderWidget properties."""

    def setUp(self):
        self.widget = RenderWidget()

    def tearDown(self):
        self.widget.deleteLater()

    def test_tool_controllers_instantiated(self):
        """ToolManager instantiates all 6 tool controllers and exposes them."""
        self.assertIsInstance(self.widget.tool_mgr, ToolManager)
        self.assertIsNotNone(self.widget.tool_mgr.selection_ctrl)
        self.assertIsNotNone(self.widget.tool_mgr.shape_ctrl)
        self.assertIsNotNone(self.widget.tool_mgr.transform_ctrl)
        self.assertIsNotNone(self.widget.tool_mgr.eyedrop_ctrl)
        self.assertIsNotNone(self.widget.tool_mgr.geometry_ctrl)
        self.assertIsNotNone(self.widget.tool_mgr.text_ctrl)

    def test_render_widget_properties_delegation(self):
        """RenderWidget property accessors transparently point to ToolManager."""
        self.assertIs(self.widget.selection_ctrl, self.widget.tool_mgr.selection_ctrl)
        self.assertIs(self.widget.shape_ctrl, self.widget.tool_mgr.shape_ctrl)
        self.assertIs(self.widget.transform_ctrl, self.widget.tool_mgr.transform_ctrl)
        self.assertIs(self.widget.eyedrop_ctrl, self.widget.tool_mgr.eyedrop_ctrl)
        self.assertIs(self.widget.geometry_ctrl, self.widget.tool_mgr.geometry_ctrl)
        self.assertIs(self.widget.text_ctrl, self.widget.tool_mgr.text_ctrl)

    def test_shape_settings_delegation(self):
        """Updating shape settings works through RenderWidget delegator."""
        self.widget.set_shape_settings({"fill_color": QtGui.QColor(255, 0, 0)})
        self.assertEqual(self.widget.shape_ctrl.settings.get("fill_color"), QtGui.QColor(255, 0, 0))

    def test_stroke_and_render_collaborators_are_instances(self):
        """Traço e pintura são colaboradores com estado próprio, não funções estáticas."""
        self.assertIsInstance(self.widget.stroke, CanvasStrokePipeline)
        self.assertIsInstance(self.widget.viewport_renderer, ViewportRenderer)
        self.assertIsNone(self.widget.stroke.last_end_screen)

    def test_brush_radius_follows_brush_size(self):
        """O raio do anel vem do tamanho do pincel que o BrushState empurra ao canvas.

        Antes havia um `_cached_brush_radius` sincronizado à mão (e relido do
        perfil do motor); a cópia podia divergir do tamanho publicado.
        """
        self.widget.brush_size = 80.0
        self.assertEqual(self.widget.current_brush_radius, 40.0)

    def test_stroke_lifecycle_signals(self):
        """Starting and ending a stroke emits strokeStarted and strokeFinished."""
        started = []
        finished = []
        self.widget.strokeStarted.connect(lambda: started.append(True))
        self.widget.strokeFinished.connect(lambda: finished.append(True))

        self.widget.start_stroke(100.0, 100.0, 0.5)
        self.assertTrue(len(started) >= 1)

        self.widget.paint_stroke(110.0, 110.0, 0.5)

        self.widget.end_stroke(110.0, 110.0)
        self.assertTrue(len(finished) >= 1)
        self.assertFalse(self.widget.drawing)


if __name__ == "__main__":
    unittest.main()
