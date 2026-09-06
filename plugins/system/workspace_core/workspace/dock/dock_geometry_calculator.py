"""DockGeometryCalculator — Geometry, Positioning, and Bounds Calculations for Docks.

Calculates global effective bounds, visual widths, and unpinned floating drawer positions.
Strictly decoupled in compliance with ARCcC v2 (< 80 LOC).
"""

from PySide6 import QtCore, QtWidgets


class DockGeometryCalculator:
    """Computes placement rectangles and global coordinate bounds for sidebar and drawer docks."""

    @staticmethod
    def compute_unpinned_geometry(
        side: str,
        workspace_w: int,
        workspace_h: int,
        drawer_w: int
    ) -> QtCore.QRect:
        """Calculates floating drawer geometry in workspace_area space, respecting the 54px sidebar slot."""
        if side == "left":
            pos_x = 54
        else:
            pos_x = max(0, workspace_w - 54 - drawer_w)
        return QtCore.QRect(pos_x, 0, drawer_w, workspace_h)

    @staticmethod
    def compute_effective_left_x(dock_widget: QtWidgets.QWidget, drawer_container: QtWidgets.QWidget) -> int:
        """Returns global X coordinate of leftmost edge of dock (including drawer if visible)."""
        base_x = dock_widget.mapToGlobal(QtCore.QPoint(0, 0)).x()
        if drawer_container and drawer_container.isVisible():
            drawer_x = drawer_container.mapToGlobal(QtCore.QPoint(0, 0)).x()
            return min(base_x, drawer_x)
        return base_x

    @staticmethod
    def compute_effective_right_x(dock_widget: QtWidgets.QWidget, drawer_container: QtWidgets.QWidget) -> int:
        """Returns global X coordinate of rightmost edge of dock (including drawer if visible)."""
        base_x = dock_widget.mapToGlobal(QtCore.QPoint(dock_widget.width(), 0)).x()
        if drawer_container and drawer_container.isVisible():
            dw = drawer_container.width()
            drawer_x = drawer_container.mapToGlobal(QtCore.QPoint(dw, 0)).x()
            return max(base_x, drawer_x)
        return base_x

    @staticmethod
    def compute_visual_width(
        dock_widget: QtWidgets.QWidget,
        sidebar: QtWidgets.QWidget,
        drawer_container: QtWidgets.QWidget,
        is_pinned: bool,
        is_open: bool
    ) -> int:
        """Returns total visual width occupied on screen (sidebar + drawer if open)."""
        if is_pinned:
            return dock_widget.width()
        w = sidebar.width() if sidebar.isVisible() else 0
        if is_open and drawer_container and drawer_container.isVisible():
            w += drawer_container.width()
        return w
