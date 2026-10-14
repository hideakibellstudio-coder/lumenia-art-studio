"""Geometry Overlay Renderer Facade.

Unifies symmetry, perspective, and ruler rendering through domain-specific sub-renderers.
The guides come in two layers: the *static* one (what only the guide state changes: lines,
rays, curves, handles) and the *hover* one (what follows the pointer). The static layer is
the expensive one (a curvilinear grid takes tens of milliseconds to stroke) and is what
`GuideOverlayCache` keeps between paints; the hover layer is cheap and drawn live.
"""

from PySide6 import QtGui
from .symmetry_overlay_renderer import SymmetryOverlayRenderer
from .perspective_grid_renderer import PerspectiveGridRenderer
from .ruler_grid_renderer import RulerGridRenderer

_PERSPECTIVE_TYPES = ("one_point", "two_point", "three_point")


class GeometryOverlayRenderer:
    """Facade for symmetry axes, rulers, 6P perspective grids, and 3D features."""

    @staticmethod
    def render_symmetry(painter: QtGui.QPainter, sym: dict, zoom: float):
        """Delegates symmetry axis rendering to SymmetryOverlayRenderer."""
        SymmetryOverlayRenderer.render_symmetry(painter, sym, zoom)

    @staticmethod
    def render_guides_static(painter: QtGui.QPainter, guide: dict, zoom: float):
        """The part of the guide that only the guide state changes."""
        gtype = guide.get("type", "none")
        if gtype == "none":
            return

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        zoom_factor = max(0.01, zoom)
        line_w = 1.2 / zoom_factor
        handle_r = 5.0 / zoom_factor

        if gtype == "straight":
            RulerGridRenderer.render_straight_ruler(painter, guide, line_w, handle_r)
        elif gtype == "curve_ruler":
            RulerGridRenderer.render_curve_ruler(painter, guide, line_w, handle_r)
        elif gtype in _PERSPECTIVE_TYPES:
            PerspectiveGridRenderer.render_perspective(painter, gtype, guide, line_w, handle_r)
        elif gtype == "isometric":
            PerspectiveGridRenderer.render_isometric(painter, line_w)
        elif gtype == "curvilinear":
            PerspectiveGridRenderer.render_curvilinear(painter, guide, line_w, handle_r, zoom_factor)

        painter.restore()

    @staticmethod
    def render_guides_hover(painter: QtGui.QPainter, ctrl, zoom: float):
        """The part that follows the pointer: parallel track, snap rays, target ring, distance badge."""
        guide = ctrl.guide_state
        gtype = guide.get("type", "none")
        if gtype in ("none", "isometric"):
            return

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        zoom_factor = max(0.01, zoom)
        line_w = 1.2 / zoom_factor
        handle_r = 5.0 / zoom_factor

        if gtype == "straight":
            RulerGridRenderer.render_straight_ruler_hover(painter, guide, line_w, handle_r, ctrl)
        elif gtype == "curve_ruler":
            RulerGridRenderer.render_curve_ruler_hover(painter, line_w, handle_r, ctrl)
        elif gtype in _PERSPECTIVE_TYPES:
            PerspectiveGridRenderer.render_perspective_hover(painter, gtype, guide, line_w, handle_r, ctrl)
        elif gtype == "curvilinear" and ctrl.dynamic_hover_curves and guide.get("show_hint", True):
            PerspectiveGridRenderer.render_curvilinear_hover(painter, ctrl, line_w, handle_r)

        painter.restore()

    @staticmethod
    def render_guides(painter: QtGui.QPainter, ctrl_or_guide, zoom: float):
        """Both layers; `ctrl_or_guide` is the tool controller (with hover) or just the guide dict (without)."""
        if hasattr(ctrl_or_guide, "guide_state"):
            GeometryOverlayRenderer.render_guides_static(painter, ctrl_or_guide.guide_state, zoom)
            GeometryOverlayRenderer.render_guides_hover(painter, ctrl_or_guide, zoom)
        else:
            GeometryOverlayRenderer.render_guides_static(painter, ctrl_or_guide, zoom)

    # Backwards compatibility delegators for tests and existing callers
    @classmethod
    def _get_cached_curvilinear_data(cls, guide: dict) -> dict:
        return PerspectiveGridRenderer.get_cached_curvilinear_data(guide)

    @staticmethod
    def _render_perspective(painter: QtGui.QPainter, gtype: str, guide: dict, line_w: float, handle_r: float):
        PerspectiveGridRenderer.render_perspective(painter, gtype, guide, line_w, handle_r)

    @staticmethod
    def _render_isometric(painter: QtGui.QPainter, line_w: float):
        PerspectiveGridRenderer.render_isometric(painter, line_w)

    @classmethod
    def _render_curvilinear(cls, painter: QtGui.QPainter, guide: dict, line_w: float, handle_r: float, zoom_factor: float):
        PerspectiveGridRenderer.render_curvilinear(painter, guide, line_w, handle_r, zoom_factor)

    @staticmethod
    def _render_curvilinear_hover(painter: QtGui.QPainter, ctrl, line_w: float, handle_r: float):
        PerspectiveGridRenderer.render_curvilinear_hover(painter, ctrl, line_w, handle_r)
