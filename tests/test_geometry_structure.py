"""Comprehensive unit tests for Camada 3 - Fase 1: Geometric Decomposition.

Tests Camera3DProjector math, GeometrySnappingEngine, specialized renderers,
GeometryOverlayRenderer Facade, and GeometryToolController.
"""

import math
import unittest
from PySide6 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

from ui.plugins.system.workspace_core.workspace.canvas.math.camera_3d_projector import (
    rotate_3d_forward,
    rotate_3d_backward,
    get_curvilinear_camera_radius,
    create_curve_from_normal,
    closest_point_on_curve
)
from ui.plugins.system.workspace_core.workspace.canvas.tools.geometry_snapping_engine import (
    GeometrySnappingEngine
)
from ui.plugins.system.workspace_core.workspace.canvas.renderers.geometry_overlay_renderer import (
    GeometryOverlayRenderer
)
from ui.plugins.system.workspace_core.workspace.canvas.tools.geometry_tool_controller import (
    GeometryToolController
)


class TestCamera3DProjector(unittest.TestCase):
    """Verifies pure 3D analytical geometry functions."""

    def test_forward_backward_rotation_inverses(self):
        """rotate_3d_forward and rotate_3d_backward must be exact inverse transformations."""
        yaw = math.radians(45.0)
        pitch = math.radians(30.0)
        x0, y0, z0 = 1.25, -0.75, 2.5

        xf, yf, zf = rotate_3d_forward(x0, y0, z0, yaw, pitch)
        xb, yb, zb = rotate_3d_backward(xf, yf, zf, yaw, pitch)

        self.assertAlmostEqual(x0, xb, places=6)
        self.assertAlmostEqual(y0, yb, places=6)
        self.assertAlmostEqual(z0, zb, places=6)

    def test_camera_radius_calculation(self):
        """Radius R calculation scales correctly with FOV."""
        r130 = get_curvilinear_camera_radius(130.0, 400.0)
        r90 = get_curvilinear_camera_radius(90.0, 400.0)
        self.assertGreater(r90, r130)
        self.assertGreater(r130, 0.0)

    def test_curve_creation_normal(self):
        """Degenerate vs circle vs line normals."""
        # Line normal (c=0)
        line = create_curve_from_normal(1.0, 0.0, 0.0, 400.0, 200.0, 200.0, "v")
        self.assertIsNotNone(line)
        self.assertEqual(line["type"], "line")

        # Circle normal (c != 0)
        circle = create_curve_from_normal(0.0, 0.0, 1.0, 400.0, 200.0, 200.0, "h")
        self.assertIsNotNone(circle)
        self.assertEqual(circle["type"], "circle")
        self.assertAlmostEqual(circle["radius"], 400.0, places=4)

    def test_closest_point_on_curve(self):
        """Finds closest point on line and circle."""
        line = {
            "type": "line",
            "p1": QtCore.QPointF(0, 100),
            "p2": QtCore.QPointF(200, 100)
        }
        pt = closest_point_on_curve(line, QtCore.QPointF(50, 150))
        self.assertAlmostEqual(pt.x(), 50.0, places=4)
        self.assertAlmostEqual(pt.y(), 100.0, places=4)

        circle = {
            "type": "circle",
            "center": QtCore.QPointF(100, 100),
            "radius": 50.0
        }
        pt_c = closest_point_on_curve(circle, QtCore.QPointF(100, 200))
        self.assertAlmostEqual(pt_c.x(), 100.0, places=4)
        self.assertAlmostEqual(pt_c.y(), 150.0, places=4)


class TestGeometrySnappingEngine(unittest.TestCase):
    """Verifies isolated snapping calculations."""

    def test_snap_straight_parallel_offset(self):
        """Straight ruler snaps with parallel contact offset."""
        guide_state = {
            "p0": QtCore.QPointF(0, 300),
            "p1": QtCore.QPointF(1000, 300),
            "snap_radius": 32.0
        }
        # Stroke started 20px below ruler at y=320 -> offset=(0, 20)
        start_dist = (0.0, 20.0)
        snapped_x, snapped_y = GeometrySnappingEngine.snap_straight(
            500.0, 350.0, 1.0, guide_state, is_stroking=True, start_distance=start_dist
        )
        self.assertAlmostEqual(snapped_x, 500.0, places=4)
        self.assertAlmostEqual(snapped_y, 320.0, places=4)

    def test_snap_bezier(self):
        """Bézier snaps precisely onto cubic path."""
        guide_state = {
            "p0": QtCore.QPointF(0, 0),
            "p1": QtCore.QPointF(300, 0),
            "p2": QtCore.QPointF(700, 400),
            "p3": QtCore.QPointF(1000, 400)
        }
        snapped_x, snapped_y = GeometrySnappingEngine.snap_bezier(500.0, 200.0, guide_state)
        # Midpoint of symmetric cubic Bézier at t=0.5:
        # bx = 0.125*0 + 0.375*300 + 0.375*700 + 0.125*1000 = 112.5 + 262.5 + 125 = 500
        # by = 0.125*0 + 0.375*0 + 0.375*400 + 0.125*400 = 150 + 50 = 200
        self.assertAlmostEqual(snapped_x, 500.0, delta=1.0)
        self.assertAlmostEqual(snapped_y, 200.0, delta=1.0)

    def test_snap_ray_perspective(self):
        """Perspective 1P ray attraction."""
        guide_state = {
            "type": "one_point",
            "vpA": QtCore.QPointF(500, 500)
        }
        start_pt = QtCore.QPointF(500, 300)
        # Moving vertically downwards towards vpA
        pt_res, locked_dir = GeometrySnappingEngine.snap_ray_perspective(
            502.0, 350.0, 1.0, guide_state, start_pt, None
        )
        self.assertIsNotNone(locked_dir)
        # Snapped x should be exactly aligned with start x=500
        self.assertAlmostEqual(pt_res[0], 500.0, delta=1.0)

    def test_snap_curvilinear_mode_filter_locks_correct_family(self):
        """Regressao Fase C3.0: snap_mode v/h/d deve travar na familia correta.

        As familias geradas por create_curve_from_normal sao sempre
        ground_v/ground_x/ground_z (ver get_dynamic_curves_at_point) -- nunca
        "*_h"/"*_d". Um filtro por sufixo ingenuo faz H e D nunca acharem
        curva nenhuma e o snap curvilineo ficar mudo nesses dois modos.
        """
        base_state = {
            "cx": 0.0, "cy": 0.0, "fov": 130.0, "pitch": 0.0, "yaw": 0.0,
            "base_radius": 400.0, "density": 30.0,
            "show_v": True, "show_h": True, "show_d": True,
            "show_ground": False, "show_ceiling": False,
        }
        click = QtCore.QPointF(120.0, 80.0)
        for mode, expected_family in (("v", "ground_v"), ("h", "ground_x"), ("d", "ground_z")):
            with self.subTest(mode=mode):
                guide_state = dict(base_state, snap_mode=mode)
                curves = GeometrySnappingEngine.get_dynamic_curves_at_point(guide_state, click)
                families = {c["family"] for c in curves}
                self.assertIn(expected_family, families, f"fixture sanity: {families}")

                _, locked = GeometrySnappingEngine.snap_curvilinear(
                    click.x(), click.y(), 1.0, guide_state, click, None, curves, True
                )
                self.assertIsNotNone(locked, f"snap_mode={mode!r} deveria travar numa curva")
                self.assertEqual(locked["family"], expected_family)


class TestGeometryDecomposedIntegration(unittest.TestCase):
    """Verifies end-to-end compatibility between controllers, facades, and renderers."""

    def test_facade_and_controller_integration(self):
        """GeometryOverlayRenderer and GeometryToolController work together without errors."""
        class MockWidget:
            backend = None

        ctrl = GeometryToolController(MockWidget())
        ctrl.center_on_document(1920, 1080)
        self.assertEqual(ctrl.sym_state["cx"], 960.0)
        self.assertEqual(ctrl.sym_state["cy"], 540.0)

        # Test hit testing
        hit = ctrl.hit_test(QtCore.QPointF(960.0, 540.0), 1.0)
        # By default mode is "none", so hit is None
        self.assertIsNone(hit)

        ctrl.sym_state["mode"] = "mirror"
        hit_sym = ctrl.hit_test(QtCore.QPointF(960.0, 540.0), 1.0)
        self.assertEqual(hit_sym, "sym_center")

        # Test rendering through Facade
        img = QtGui.QImage(400, 300, QtGui.QImage.Format_ARGB32_Premultiplied)
        img.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(img)

        try:
            GeometryOverlayRenderer.render_symmetry(painter, ctrl.sym_state, 1.0)
            ctrl.guide_state["type"] = "straight"
            GeometryOverlayRenderer.render_guides(painter, ctrl, 1.0)

            ctrl.guide_state["type"] = "curvilinear"
            GeometryOverlayRenderer.render_guides(painter, ctrl, 1.0)
        finally:
            painter.end()


if __name__ == "__main__":
    unittest.main()
