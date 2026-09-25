"""Geometry Overlay Renderer Facade.

Unifies symmetry, perspective, and ruler rendering through domain-specific sub-renderers.
Maintains 100% backwards compatibility while complying with ARCcC v2 (< 85 LOC).
"""

from PySide6 import QtGui
from ..math.camera_3d_projector import (
    rotate_3d_backward,
    rotate_3d_forward,
    create_curve_from_normal,
    p3d_to_2d_fisheye
)
from .symmetry_overlay_renderer import SymmetryOverlayRenderer
from .perspective_grid_renderer import PerspectiveGridRenderer
from .ruler_grid_renderer import RulerGridRenderer


class GeometryOverlayRenderer:
    """Facade for symmetry axes, rulers, 6P perspective grids, and 3D features."""

    @staticmethod
    def render_symmetry(painter: QtGui.QPainter, sym: dict, zoom: float):
        """Delegates symmetry axis rendering to SymmetryOverlayRenderer."""
        SymmetryOverlayRenderer.render_symmetry(painter, sym, zoom)

    @staticmethod
    def render_guides(painter: QtGui.QPainter, ctrl_or_guide, zoom: float):
        """Dispatches guide rendering to domain-specific specialized renderers."""
        guide = ctrl_or_guide.guide_state if hasattr(ctrl_or_guide, "guide_state") else ctrl_or_guide
        gtype = guide.get("type", "none")
        if gtype == "none":
            return

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        zoom_factor = max(0.01, zoom)
        line_w = 1.2 / zoom_factor
        handle_r = 5.0 / zoom_factor

        if gtype == "straight":
            RulerGridRenderer.render_straight_ruler(painter, guide, line_w, handle_r, ctrl_or_guide)
        elif gtype == "curve_ruler":
            RulerGridRenderer.render_curve_ruler(painter, guide, line_w, handle_r, ctrl_or_guide)
        elif gtype in ("one_point", "two_point", "three_point"):
            PerspectiveGridRenderer.render_perspective(painter, gtype, guide, line_w, handle_r, ctrl_or_guide)
        elif gtype == "isometric":
            PerspectiveGridRenderer.render_isometric(painter, line_w)
        elif gtype == "curvilinear":
            PerspectiveGridRenderer.render_curvilinear(painter, guide, line_w, handle_r, zoom_factor)
            if hasattr(ctrl_or_guide, "dynamic_hover_curves") and ctrl_or_guide.dynamic_hover_curves and guide.get("show_hint", True):
                PerspectiveGridRenderer.render_curvilinear_hover(painter, ctrl_or_guide, line_w, handle_r)

        painter.restore()

    # Backwards compatibility delegators for tests and existing callers
    @classmethod
    def _get_cached_curvilinear_data(cls, guide: dict) -> dict:
        return PerspectiveGridRenderer.get_cached_curvilinear_data(guide)

    @staticmethod
    def _render_perspective(painter: QtGui.QPainter, gtype: str, guide: dict, line_w: float, handle_r: float, ctrl=None):
        PerspectiveGridRenderer.render_perspective(painter, gtype, guide, line_w, handle_r, ctrl)

    @staticmethod
    def _render_isometric(painter: QtGui.QPainter, line_w: float):
        PerspectiveGridRenderer.render_isometric(painter, line_w)

    @classmethod
    def _render_curvilinear(cls, painter: QtGui.QPainter, guide: dict, line_w: float, handle_r: float, zoom_factor: float):
        PerspectiveGridRenderer.render_curvilinear(painter, guide, line_w, handle_r, zoom_factor)

    @staticmethod
    def _render_curvilinear_hover(painter: QtGui.QPainter, ctrl, line_w: float, handle_r: float):
        PerspectiveGridRenderer.render_curvilinear_hover(painter, ctrl, line_w, handle_r)
