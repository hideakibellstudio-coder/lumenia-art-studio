"""Straight and Curve Ruler Renderer.

Renders infinite straight rulers with Infinite Painter parallel cursor tracking,
distance badges, and cubic Bézier curve guides with interactive control points.
Strictly decoupled in compliance with ARCcC v2 (< 120 LOC).
"""

import math
from PySide6 import QtCore, QtGui


class RulerGridRenderer:
    """Renders straight and Bézier rulers with interactive handles and snap feedback."""

    @staticmethod
    def render_straight_ruler(painter: QtGui.QPainter, guide: dict, line_w: float, handle_r: float, ctrl=None):
        """Renders infinite straight line guide with endpoint handles and parallel track feedback."""
        p0 = guide.get("p0", QtCore.QPointF(0, 300))
        p1 = guide.get("p1", QtCore.QPointF(800, 300))
        dx, dy = p1.x() - p0.x(), p1.y() - p0.y()
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length

        # Infinite guide ray
        pen_guide = QtGui.QPen(QtGui.QColor(59, 130, 246, 200), line_w, QtCore.Qt.DashLine)
        painter.setPen(pen_guide)
        painter.drawLine(QtCore.QPointF(p0.x() - 8000.0 * ux, p0.y() - 8000.0 * uy), QtCore.QPointF(p1.x() + 8000.0 * ux, p1.y() + 8000.0 * uy))

        # Endpoint handles
        painter.setBrush(QtGui.QColor(59, 130, 246, 220))
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), line_w))
        painter.drawEllipse(p0, handle_r, handle_r)
        painter.drawEllipse(p1, handle_r, handle_r)

        # Parallel track & distance badge
        if ctrl and hasattr(ctrl, "hover_point") and ctrl.hover_point is not None:
            hpt = ctrl.hover_point
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 125, 45, 180), line_w * 1.3, QtCore.Qt.DashLine))
            painter.drawLine(QtCore.QPointF(hpt.x() - 4000.0 * ux, hpt.y() - 4000.0 * uy), QtCore.QPointF(hpt.x() + 4000.0 * ux, hpt.y() + 4000.0 * uy))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 125, 45, 230), line_w * 1.5))
            painter.drawEllipse(hpt, handle_r * 1.3, handle_r * 1.3)
            if getattr(ctrl, "is_stroking", False) and getattr(ctrl, "snap_start_pt", None) is not None:
                dist = math.hypot(hpt.x() - ctrl.snap_start_pt.x(), hpt.y() - ctrl.snap_start_pt.y())
                painter.setFont(QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold))
                painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 220)))
                painter.drawText(int(hpt.x() + 12), int(hpt.y() - 6), f"{int(dist)} px")

    @staticmethod
    def render_curve_ruler(painter: QtGui.QPainter, guide: dict, line_w: float, handle_r: float, ctrl=None):
        """Renders 4-point cubic Bézier ruler with control handles and tangent lines."""
        p0 = guide.get("p0", QtCore.QPointF(100, 300))
        p1 = guide.get("p1", QtCore.QPointF(250, 150))
        p2 = guide.get("p2", QtCore.QPointF(550, 150))
        p3 = guide.get("p3", QtCore.QPointF(700, 300))

        pen_guide = QtGui.QPen(QtGui.QColor(59, 130, 246, 200), line_w, QtCore.Qt.DashLine)
        painter.setPen(pen_guide)

        path = QtGui.QPainterPath()
        path.moveTo(p0)
        path.cubicTo(p1, p2, p3)
        painter.drawPath(path)

        painter.setPen(QtGui.QPen(QtGui.QColor(59, 130, 246, 120), line_w * 0.8, QtCore.Qt.DotLine))
        painter.drawLine(p0, p1)
        painter.drawLine(p3, p2)

        painter.setBrush(QtGui.QColor(59, 130, 246, 220))
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), line_w))
        for pt in (p0, p1, p2, p3):
            painter.drawEllipse(pt, handle_r, handle_r)

        if ctrl and hasattr(ctrl, "hover_point") and ctrl.hover_point is not None:
            hpt = ctrl.hover_point
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 125, 45, 230), line_w * 1.5))
            painter.drawEllipse(hpt, handle_r * 1.3, handle_r * 1.3)
