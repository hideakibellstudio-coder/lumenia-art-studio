"""Canvas Background and Transparency Pattern Renderer.

Generates the transparency checkerboard brush and renders canvas paper/background.
Strictly decoupled in compliance with ARCcC v2 (< 60 LOC).
"""

from PySide6 import QtCore, QtGui


class CanvasBackgroundRenderer:
    """Renders canvas transparency checkerboards and paper backgrounds."""

    @staticmethod
    def create_checker_brush() -> QtGui.QBrush:
        """Creates a 32x32 two-tone checkerboard pattern brush for transparent layers."""
        pix = QtGui.QPixmap(32, 32)
        p = QtGui.QPainter(pix)
        p.fillRect(0, 0, 16, 16, QtGui.QColor("#ffffff"))
        p.fillRect(16, 0, 16, 16, QtGui.QColor("#d1d5db"))
        p.fillRect(0, 16, 16, 16, QtGui.QColor("#d1d5db"))
        p.fillRect(16, 16, 16, 16, QtGui.QColor("#ffffff"))
        p.end()
        return QtGui.QBrush(pix)

    @staticmethod
    def render_background(
        painter: QtGui.QPainter,
        rect: QtCore.QRect,
        paper_visible: bool,
        paper_color: QtGui.QColor,
        checker_brush: QtGui.QBrush
    ) -> None:
        """Paints either solid paper color or transparency checkerboard on the target rect."""
        if rect.isEmpty():
            return
        painter.fillRect(rect, paper_color if paper_visible else checker_brush)
