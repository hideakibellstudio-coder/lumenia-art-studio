"""Vector and Geometric Shape Tool Controller."""

import math
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.engine.registry import EngineRegistry

class ShapeToolController:
    """Controlador de desenho e rasterização de formas vetoriais no ALADYN ENGINE."""

    def __init__(self, widget):
        self.widget = widget
        self.settings: dict = {
            "shape_type": "shape_line",
            "draw_mode": "both",
            "stroke_width": 4,
            "stroke_color": QtGui.QColor(0, 0, 0, 255),
            "fill_color": QtGui.QColor(0, 0, 0, 255),
            "corner_radius": 0,
            "polygon_sides": 5,
            "star_points": 5,
            "star_inner_ratio": 0.5,
        }
        self.drag_active: bool = False
        self.drag_start: QtCore.QPointF = QtCore.QPointF(0, 0)
        self.drag_current: QtCore.QPointF = QtCore.QPointF(0, 0)

    def calculate_path(self):
        p1 = self.drag_start
        p2 = self.drag_current

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        is_shift = bool(modifiers & QtCore.Qt.ShiftModifier)
        is_alt = bool(modifiers & QtCore.Qt.AltModifier)

        shape_type = self.settings.get("shape_type", "shape_line")
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()

        if shape_type == "shape_line":
            if is_shift:
                length = math.hypot(dx, dy)
                if length > 1e-4:
                    raw_ang = math.atan2(dy, dx)
                    snap_step = math.radians(15.0)
                    snapped_ang = round(raw_ang / snap_step) * snap_step
                    p2 = QtCore.QPointF(p1.x() + length * math.cos(snapped_ang), p1.y() + length * math.sin(snapped_ang))
            if is_alt:
                p_start = QtCore.QPointF(p1.x() - (p2.x() - p1.x()), p1.y() - (p2.y() - p1.y()))
                path = QtGui.QPainterPath()
                path.moveTo(p_start)
                path.lineTo(p2)
                return path
            else:
                path = QtGui.QPainterPath()
                path.moveTo(p1)
                path.lineTo(p2)
                return path

        elif shape_type == "shape_rect":
            if is_shift:
                side = max(abs(dx), abs(dy))
                dx = side if dx >= 0 else -side
                dy = side if dy >= 0 else -side

            if is_alt:
                rx = abs(dx)
                ry = abs(dy)
                rect = QtCore.QRectF(p1.x() - rx, p1.y() - ry, rx * 2.0, ry * 2.0)
            else:
                rect = QtCore.QRectF(min(p1.x(), p1.x() + dx), min(p1.y(), p1.y() + dy), abs(dx), abs(dy))

            radius = float(self.settings.get("corner_radius", 0))
            path = QtGui.QPainterPath()
            if radius > 0:
                max_r = min(rect.width(), rect.height()) / 2.0
                r = min(radius, max_r)
                path.addRoundedRect(rect, r, r)
            else:
                path.addRect(rect)
            return path

        elif shape_type == "shape_ellipse":
            if is_shift:
                side = max(abs(dx), abs(dy))
                dx = side if dx >= 0 else -side
                dy = side if dy >= 0 else -side

            if is_alt:
                rx = abs(dx)
                ry = abs(dy)
                rect = QtCore.QRectF(p1.x() - rx, p1.y() - ry, rx * 2.0, ry * 2.0)
            else:
                rect = QtCore.QRectF(min(p1.x(), p1.x() + dx), min(p1.y(), p1.y() + dy), abs(dx), abs(dy))

            path = QtGui.QPainterPath()
            path.addEllipse(rect)
            return path

        elif shape_type == "shape_polygon":
            sides = max(3, int(self.settings.get("polygon_sides", 5)))
            radius = math.hypot(dx, dy)
            if radius < 1.0:
                return None
            start_ang = math.atan2(dy, dx)
            if is_shift:
                snap_step = math.radians(15.0)
                start_ang = round(start_ang / snap_step) * snap_step

            center = p1 if is_alt else QtCore.QPointF(p1.x() + dx / 2.0, p1.y() + dy / 2.0)
            if not is_alt:
                radius = math.hypot(dx, dy) / 2.0

            poly = QtGui.QPolygonF()
            for i in range(sides):
                ang = start_ang + (2.0 * math.pi * i) / sides
                x = center.x() + radius * math.cos(ang)
                y = center.y() + radius * math.sin(ang)
                poly.append(QtCore.QPointF(x, y))

            path = QtGui.QPainterPath()
            path.addPolygon(poly)
            path.closeSubpath()
            return path

        elif shape_type == "shape_star":
            points = max(3, int(self.settings.get("star_points", 5)))
            r_outer = math.hypot(dx, dy)
            if r_outer < 1.0:
                return None
            inner_ratio = float(self.settings.get("star_inner_ratio", 0.5))
            r_inner = r_outer * inner_ratio

            start_ang = math.atan2(dy, dx)
            if is_shift:
                snap_step = math.radians(15.0)
                start_ang = round(start_ang / snap_step) * snap_step

            center = p1 if is_alt else QtCore.QPointF(p1.x() + dx / 2.0, p1.y() + dy / 2.0)
            if not is_alt:
                r_outer /= 2.0
                r_inner /= 2.0

            poly = QtGui.QPolygonF()
            total_vertices = points * 2
            for i in range(total_vertices):
                ang = start_ang + (math.pi * i) / points
                r = r_outer if (i % 2 == 0) else r_inner
                x = center.x() + r * math.cos(ang)
                y = center.y() + r * math.sin(ang)
                poly.append(QtCore.QPointF(x, y))

            path = QtGui.QPainterPath()
            path.addPolygon(poly)
            path.closeSubpath()
            return path

        return None

    def commit_to_layer(self):
        path = self.calculate_path()
        if not path:
            self.widget.update()
            return

        shape_type = self.settings.get("shape_type", "shape_line")
        draw_mode = self.settings.get("draw_mode", "both")
        stroke_w = float(self.settings.get("stroke_width", 4))
        stroke_col = QtGui.QColor(self.settings.get("stroke_color", QtGui.QColor(0, 0, 0, 255)))
        fill_col = QtGui.QColor(self.settings.get("fill_color", QtGui.QColor(0, 0, 0, 255)))

        shape_img = QtGui.QImage(self.widget.canvas_w, self.widget.canvas_h, QtGui.QImage.Format_ARGB32_Premultiplied)
        shape_img.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(shape_img)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        pen = QtGui.QPen(stroke_col, stroke_w, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin) if draw_mode in ("both", "stroke") else QtCore.Qt.NoPen
        brush = QtGui.QBrush(fill_col) if (draw_mode in ("both", "fill") and shape_type != "shape_line") else QtCore.Qt.NoBrush

        painter.setPen(pen)
        painter.setBrush(brush)

        if isinstance(path, QtGui.QPainterPath):
            painter.drawPath(path)
        elif isinstance(path, QtCore.QLineF):
            painter.drawLine(path)
        elif isinstance(path, QtCore.QRectF):
            painter.drawRect(path)

        painter.end()

        shape_rgba = shape_img.convertToFormat(QtGui.QImage.Format_RGBA8888)
        ptr = shape_rgba.constBits()
        px_bytes = ptr.tobytes()

        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "paste_rgba_buffer_on_active_layer") and getattr(backend, "available", False):
            backend.paste_rgba_buffer_on_active_layer(0, 0, self.widget.canvas_w, self.widget.canvas_h, px_bytes)
        else:
            self.widget._flood_layers.append(shape_img)
            self.widget._flood_redo_stack.clear()

        self.widget.update()
        self.widget.strokeFinished.emit()
