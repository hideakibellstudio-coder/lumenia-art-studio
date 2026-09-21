"""Perspective and Curvilinear 6P Grid Renderer.

Handles 1-Point, 2-Point, 3-Point, Isometric and Curvilinear 6P Fisheye
perspective guides, 3D cubes, horizon lines, vanishing points, and hover hints.
Strictly decoupled in compliance with ARCcC v2 (< 250 LOC).
"""

import math
from PySide6 import QtCore, QtGui

from ui.core.theme.manager import ThemeManager

from ..math.curvilinear_mesh_builder import CurvilinearMeshBuilder


class PerspectiveGridRenderer:
    """Renders 1P/2P/3P linear perspectives, isometric grids, and 6P curvilinear fisheye overlays."""

    @classmethod
    def get_cached_curvilinear_data(cls, guide: dict) -> dict:
        """Delegates 3D curvilinear data computation and caching to CurvilinearMeshBuilder."""
        return CurvilinearMeshBuilder.get_cached_curvilinear_data(guide)

    @staticmethod
    def render_perspective(painter: QtGui.QPainter, gtype: str, guide: dict, line_w: float, handle_r: float, ctrl=None):
        """Renders 1P, 2P, or 3P perspective vanishing points, horizon, and rays."""
        vps = []
        if gtype in ("one_point", "two_point", "three_point"):
            vps.append(guide.get("vpA", QtCore.QPointF(400, 300)))
        if gtype in ("two_point", "three_point"):
            vps.append(guide.get("vpB", QtCore.QPointF(-600, 300)))
        if gtype == "three_point":
            vps.append(guide.get("vpC", QtCore.QPointF(400, -1200)))

        if len(vps) >= 2:
            painter.setPen(QtGui.QPen(QtGui.QColor(234, 88, 12, 180), line_w * 1.5))
            painter.drawLine(QtCore.QPointF(-8000, vps[0].y()), QtCore.QPointF(8000, vps[0].y()))

        tm = ThemeManager.instance()
        handle_border_col = QtGui.QColor(tm.get_color("GUIDE_HANDLE_BORDER", "#ffffff"))
        hover_base_col = QtGui.QColor(tm.get_color("GUIDE_HOVER_POINT", "#ff7d2d"))
        hover_point_col = QtGui.QColor(hover_base_col.red(), hover_base_col.green(), hover_base_col.blue(), 230)
        dist_base_col = QtGui.QColor(tm.get_color("GUIDE_DISTANCE_TEXT", "#ffffff"))
        dist_text_col = QtGui.QColor(dist_base_col.red(), dist_base_col.green(), dist_base_col.blue(), 220)

        for vp in vps:
            painter.setBrush(QtGui.QColor(234, 88, 12, 220))
            painter.setPen(QtGui.QPen(handle_border_col, line_w))
            painter.drawEllipse(vp, handle_r * 1.2, handle_r * 1.2)
            painter.setPen(QtGui.QPen(QtGui.QColor(234, 88, 12, 90), line_w, QtCore.Qt.DashLine))
            for deg in range(0, 360, 20):
                rad = math.radians(deg)
                painter.drawLine(vp, QtCore.QPointF(vp.x() + 4000.0 * math.cos(rad), vp.y() + 4000.0 * math.sin(rad)))

        if ctrl and hasattr(ctrl, "hover_point") and ctrl.hover_point is not None:
            hpt = ctrl.hover_point
            pen_active = QtGui.QPen(QtGui.QColor(255, 125, 45, 210), line_w * 1.5, QtCore.Qt.DashLine)
            painter.setPen(pen_active)
            for vp in vps:
                dx, dy = hpt.x() - vp.x(), hpt.y() - vp.y()
                l = math.hypot(dx, dy)
                if l > 1e-4:
                    ux, uy = dx / l, dy / l
                    painter.drawLine(vp, QtCore.QPointF(hpt.x() + ux * 4000.0, hpt.y() + uy * 4000.0))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(QtGui.QPen(hover_point_col, line_w * 1.5))
            painter.drawEllipse(hpt, handle_r * 1.3, handle_r * 1.3)
            if getattr(ctrl, "is_stroking", False) and getattr(ctrl, "snap_start_pt", None) is not None:
                dist = math.hypot(hpt.x() - ctrl.snap_start_pt.x(), hpt.y() - ctrl.snap_start_pt.y())
                painter.setFont(QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold))
                painter.setPen(QtGui.QPen(dist_text_col))
                painter.drawText(int(hpt.x() + 12), int(hpt.y() - 6), f"{int(dist)} px")

    @staticmethod
    def render_isometric(painter: QtGui.QPainter, line_w: float):
        """Renders standard 30-degree isometric drawing grid."""
        painter.setPen(QtGui.QPen(QtGui.QColor(59, 130, 246, 75), line_w, QtCore.Qt.DashLine))
        spacing = 80.0
        tan_30 = math.tan(math.pi / 6)
        for i in range(-50, 50):
            y_base = i * spacing
            painter.drawLine(QtCore.QPointF(-4000, y_base - 4000 * tan_30), QtCore.QPointF(4000, y_base + 4000 * tan_30))
            painter.drawLine(QtCore.QPointF(-4000, y_base + 4000 * tan_30), QtCore.QPointF(4000, y_base - 4000 * tan_30))
            painter.drawLine(QtCore.QPointF(i * spacing, -4000), QtCore.QPointF(i * spacing, 4000))

    @classmethod
    def render_curvilinear(cls, painter: QtGui.QPainter, guide: dict, line_w: float, handle_r: float, zoom_factor: float):
        """Renders 6P curvilinear fisheye grid, bounding ring, paths, and handles."""
        data = cls.get_cached_curvilinear_data(guide)
        cx, cy, R = data["cx"], data["cy"], data["R"]
        yaw_rad = data["yaw_rad"]

        has_ring = guide.get("show_ring", True)
        if has_ring:
            painter.setPen(QtGui.QPen(QtGui.QColor(168, 85, 247, 220), line_w * 1.5))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawEllipse(QtCore.QPointF(cx, cy), R, R)
            clip = QtGui.QPainterPath()
            clip.addEllipse(QtCore.QPointF(cx, cy), R, R)
            painter.save()
            painter.setClipPath(clip)

        if guide.get("show_ground", False) and not data["ground_path"].isEmpty():
            painter.setPen(QtGui.QPen(QtGui.QColor(100, 200, 150, 70), line_w, QtCore.Qt.SolidLine))
            painter.drawPath(data["ground_path"])

        if guide.get("show_ground_verticals", False) and not data["gv_path"].isEmpty():
            painter.setPen(QtGui.QPen(QtGui.QColor(100, 150, 255, 60), line_w, QtCore.Qt.DashLine))
            painter.drawPath(data["gv_path"])

        if guide.get("show_ceiling", False) and not data["ceiling_path"].isEmpty():
            painter.setPen(QtGui.QPen(QtGui.QColor(200, 150, 100, 70), line_w, QtCore.Qt.SolidLine))
            painter.drawPath(data["ceiling_path"])

        if guide.get("show_ceiling_verticals", False) and not data["cv_path"].isEmpty():
            painter.setPen(QtGui.QPen(QtGui.QColor(200, 100, 100, 60), line_w, QtCore.Qt.DashLine))
            painter.drawPath(data["cv_path"])

        if guide.get("show_cube", False) and not data["cube_path"].isEmpty():
            painter.setPen(QtGui.QPen(QtGui.QColor(150, 100, 255, 180), line_w * 1.4))
            painter.drawPath(data["cube_path"])

        if guide.get("show_v", True) and data["v_curves"]:
            painter.setPen(QtGui.QPen(QtGui.QColor(90, 140, 255, 110), line_w, QtCore.Qt.DashLine))
            for curv in data["v_curves"]:
                if curv["type"] == "line":
                    painter.drawLine(curv["p1"], curv["p2"])
                else:
                    painter.drawEllipse(curv["center"], curv["radius"], curv["radius"])

        if guide.get("show_h", True) and data["h_curves"]:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 90, 130, 110), line_w, QtCore.Qt.DashLine))
            for curv in data["h_curves"]:
                if curv["type"] == "line":
                    painter.drawLine(curv["p1"], curv["p2"])
                else:
                    painter.drawEllipse(curv["center"], curv["radius"], curv["radius"])

        if guide.get("show_d", True) and data["d_curves"]:
            painter.setPen(QtGui.QPen(QtGui.QColor(90, 210, 130, 110), line_w, QtCore.Qt.DashLine))
            for curv in data["d_curves"]:
                if curv["type"] == "line":
                    painter.drawLine(curv["p1"], curv["p2"])
                else:
                    painter.drawEllipse(curv["center"], curv["radius"], curv["radius"])

        if guide.get("show_vps", False) and data["vps"]:
            font = QtGui.QFont("Segoe UI", max(6, int(8 / max(0.01, line_w))), QtGui.QFont.Bold)
            painter.setFont(font)
            for name, pt, col in data["vps"]:
                painter.setBrush(col)
                painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), line_w))
                painter.drawEllipse(pt, handle_r * 0.8, handle_r * 0.8)
                painter.setPen(QtGui.QPen(col))
                painter.drawText(int(pt.x() + 6), int(pt.y() + 4), name)

        if has_ring:
            painter.restore()

        if guide.get("show_letterbox", False) and data["letterbox_rect"]:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 120), line_w * 1.5))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(data["letterbox_rect"])

        # Central Pivot & Interactive Rotation Arm (80px)
        cos_y, sin_y = math.cos(yaw_rad), math.sin(yaw_rad)
        arm_len = 80.0 / zoom_factor
        hx, hy = cx + arm_len * cos_y, cy + arm_len * sin_y
        painter.setPen(QtGui.QPen(QtGui.QColor(150, 100, 255, 140), line_w * 1.5))
        painter.drawLine(QtCore.QPointF(cx, cy), QtCore.QPointF(hx, hy))

        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 180), line_w))
        painter.setBrush(QtGui.QColor(100, 200, 255, 240))
        painter.drawEllipse(QtCore.QPointF(hx, hy), handle_r * 1.1, handle_r * 1.1)

        painter.setBrush(QtGui.QColor(255, 255, 255, 240))
        painter.drawEllipse(QtCore.QPointF(cx, cy), handle_r * 1.2, handle_r * 1.2)

    @staticmethod
    def render_curvilinear_hover(painter: QtGui.QPainter, ctrl, line_w: float, handle_r: float):
        """Renders dynamic curvilinear orthogonal curves and hollow target badge at cursor point."""
        cx, cy = ctrl.guide_state.get("cx", 400.0), ctrl.guide_state.get("cy", 300.0)
        fov_rad = math.radians(ctrl.guide_state.get("fov", 130.0))
        tan_f = math.tan(fov_rad / 4.0)
        base_r = ctrl.guide_state.get("base_radius", 400.0)
        R = base_r / tan_f if tan_f > 1e-5 else 1e9

        has_ring = ctrl.guide_state.get("show_ring", True)
        if has_ring:
            clip = QtGui.QPainterPath()
            clip.addEllipse(QtCore.QPointF(cx, cy), R, R)
            painter.save()
            painter.setClipPath(clip)

        curves_to_draw = ctrl.dynamic_hover_curves
        mode = ctrl.guide_state.get("snap_mode", "auto")
        if not ctrl.is_stroking and mode in ("v", "h", "d"):
            curves_to_draw = [c for c in curves_to_draw if c.get("family") == mode or c.get("family", "").endswith(f"_{mode}")]

        painter.setBrush(QtCore.Qt.NoBrush)
        for c in curves_to_draw:
            fam = c.get("family", "")
            if fam.endswith("_v") or fam == "v":
                c_col = QtGui.QColor(56, 189, 248, 120)
            elif fam.endswith("_x") or fam == "h":
                c_col = QtGui.QColor(248, 113, 113, 120)
            elif fam.endswith("_z") or fam == "d":
                c_col = QtGui.QColor(74, 222, 128, 120)
            else:
                c_col = QtGui.QColor(255, 125, 45, 100)

            painter.setPen(QtGui.QPen(c_col, line_w * 1.3, QtCore.Qt.DashLine))
            if c["type"] == "line":
                painter.drawLine(c["p1"], c["p2"])
            elif c["type"] == "polyline":
                pts = c.get("points", [])
                if len(pts) >= 2:
                    path = QtGui.QPainterPath()
                    path.moveTo(pts[0])
                    for p in pts[1:]:
                        path.lineTo(p)
                    painter.drawPath(path)
            else:
                painter.drawEllipse(c["center"], c["radius"], c["radius"])

        tm = ThemeManager.instance()
        hover_base_col = QtGui.QColor(tm.get_color("GUIDE_HOVER_POINT", "#ff7d2d"))
        hover_point_col = QtGui.QColor(hover_base_col.red(), hover_base_col.green(), hover_base_col.blue(), 230)
        dist_base_col = QtGui.QColor(tm.get_color("GUIDE_DISTANCE_TEXT", "#ffffff"))
        dist_text_col = QtGui.QColor(dist_base_col.red(), dist_base_col.green(), dist_base_col.blue(), 220)

        if ctrl.hover_point is not None:
            hpt = ctrl.hover_point
            painter.setPen(QtGui.QPen(hover_point_col, line_w * 1.5))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawEllipse(hpt, handle_r * 1.3, handle_r * 1.3)
            if getattr(ctrl, "is_stroking", False) and getattr(ctrl, "snap_start_pt", None) is not None:
                dist = math.hypot(hpt.x() - ctrl.snap_start_pt.x(), hpt.y() - ctrl.snap_start_pt.y())
                painter.setFont(QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold))
                painter.setPen(QtGui.QPen(dist_text_col))
                painter.drawText(int(hpt.x() + 12), int(hpt.y() - 6), f"{int(dist)} px")

        if has_ring:
            painter.restore()
