"""Symmetry Guide and Axis Renderer.

Renders bilateral, horizontal/vertical mirror, double mirror, radial,
and kaleidoscope symmetry axes with interactive pivot and angle handles.
Strictly decoupled in compliance with ARCcC v2 (< 100 LOC).
"""

import math
from PySide6 import QtCore, QtGui


class SymmetryOverlayRenderer:
    """Renders symmetry axes, divisions, and control handles."""

    @staticmethod
    def render_symmetry(painter: QtGui.QPainter, sym: dict, zoom: float):
        """Draws active symmetry axes and interactive control handles."""
        mode = sym.get("mode", "none")
        if mode == "none":
            return

        cx, cy = sym.get("cx", 400.0), sym.get("cy", 300.0)
        angle_rad = math.radians(sym.get("angle", 90.0))
        if mode == "mirror_v":
            angle_rad = math.pi / 2.0
        elif mode == "mirror_h":
            angle_rad = 0.0
        elif mode == "double_mirror" and sym.get("angle", 90.0) == 0.0:
            angle_rad = math.pi / 2.0
        segments = max(2, sym.get("segments", 6))

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        zoom_factor = max(0.01, zoom)
        line_w = 1.5 / zoom_factor

        pen_line = QtGui.QPen(QtGui.QColor(168, 85, 247, 210), line_w)
        pen_line.setStyle(QtCore.Qt.SolidLine if mode in ("kaleidoscope", "double_mirror") else QtCore.Qt.DashLine)
        painter.setPen(pen_line)

        r = 8000.0
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)

        if mode in ("mirror", "mirror_v", "mirror_h"):
            painter.drawLine(QtCore.QPointF(cx - r * cos_a, cy - r * sin_a), QtCore.QPointF(cx + r * cos_a, cy + r * sin_a))
        elif mode == "double_mirror":
            painter.drawLine(QtCore.QPointF(cx - r * cos_a, cy - r * sin_a), QtCore.QPointF(cx + r * cos_a, cy + r * sin_a))
            painter.drawLine(QtCore.QPointF(cx + r * sin_a, cy - r * cos_a), QtCore.QPointF(cx - r * sin_a, cy + r * sin_a))
        elif mode in ("radial", "kaleidoscope"):
            step = (2.0 * math.pi) / segments
            for i in range(segments):
                a = angle_rad + i * step
                painter.drawLine(QtCore.QPointF(cx, cy), QtCore.QPointF(cx + r * math.cos(a), cy + r * math.sin(a)))

        handle_r = 6.0 / zoom_factor
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 240), line_w))
        painter.setBrush(QtGui.QColor(168, 85, 247, 220))
        painter.drawEllipse(QtCore.QPointF(cx, cy), handle_r, handle_r)

        hx, hy = cx + (80.0 / zoom_factor) * cos_a, cy + (80.0 / zoom_factor) * sin_a
        painter.setBrush(QtGui.QColor(236, 72, 153, 220))
        painter.drawEllipse(QtCore.QPointF(hx, hy), handle_r * 0.9, handle_r * 0.9)
        painter.drawLine(QtCore.QPointF(cx, cy), QtCore.QPointF(hx, hy))
        painter.restore()
