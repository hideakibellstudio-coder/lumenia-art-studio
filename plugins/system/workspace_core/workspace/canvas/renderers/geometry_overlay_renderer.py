"""Renderer for Symmetry, Perspective (1P, 2P, 3P, Curvilinear 6P) and Rulers.

Complete mathematical alignment with 3D camera rotation and soft transparent guide hint.
"""

import math
from PySide6 import QtCore, QtGui


def rotate_3d_backward(x, y, z, yaw_rad, pitch_rad):
    cos_h, sin_h = math.cos(yaw_rad), math.sin(yaw_rad)
    cos_v, sin_v = math.cos(pitch_rad), math.sin(pitch_rad)
    x_unp = x
    y_unp = y * cos_v + z * sin_v
    z_unp = -y * sin_v + z * cos_v
    x_unrot = x_unp * cos_h + z_unp * sin_h
    y_unrot = y_unp
    z_unrot = -x_unp * sin_h + z_unp * cos_h
    return x_unrot, y_unrot, z_unrot


def create_curve_from_normal(a, b, c, R, cx, cy, family):
    norm = math.sqrt(a * a + b * b + c * c)
    if norm > 1e-6: a, b, c = a / norm, b / norm, c / norm
    if abs(c) < 1e-4:
        denom = math.sqrt(a * a + b * b)
        if denom < 1e-4: return None
        dx, dy = -b / denom, -a / denom
        return {"type": "line", "family": family, "p1": QtCore.QPointF(cx + dx * 20000.0, cy + dy * 20000.0),
                "p2": QtCore.QPointF(cx - dx * 20000.0, cy - dy * 20000.0), "dir": QtCore.QPointF(dx, dy)}
    else:
        cx_c, cy_c, radius = -R * a / c, R * b / c, R / abs(c)
        if radius > 20000.0:
            dist = math.hypot(cx_c, cy_c)
            if dist < 1e-4: return None
            nx, ny = cx_c / dist, cy_c / dist
            d_cl = dist - radius
            c_x, c_y = cx + d_cl * nx, cy + d_cl * ny
            return {"type": "line", "family": family, "p1": QtCore.QPointF(c_x - ny * 20000.0, c_y + nx * 20000.0),
                    "p2": QtCore.QPointF(c_x + ny * 20000.0, c_y - nx * 20000.0), "dir": QtCore.QPointF(-ny, nx)}
        return {"type": "circle", "family": family, "center": QtCore.QPointF(cx + cx_c, cy + cy_c), "radius": radius}


class GeometryOverlayRenderer:
    """Renders symmetry axes, rulers, 6P perspective grids, 3D features and letterbox."""

    @staticmethod
    def render_symmetry(painter: QtGui.QPainter, sym: dict, zoom: float):
        mode = sym.get("mode", "none")
        if mode == "none" or sym.get("hidden", False): return

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

    @staticmethod
    def render_guides(painter: QtGui.QPainter, ctrl_or_guide, zoom: float):
        guide = ctrl_or_guide.guide_state if hasattr(ctrl_or_guide, "guide_state") else ctrl_or_guide
        gtype = guide.get("type", "none")
        if gtype == "none" or guide.get("hidden", False): return

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        zoom_factor = max(0.01, zoom)
        line_w = 1.2 / zoom_factor
        handle_r = 5.0 / zoom_factor

        pen_guide = QtGui.QPen(QtGui.QColor(59, 130, 246, 200), line_w, QtCore.Qt.DashLine)
        painter.setPen(pen_guide)

        if gtype == "straight":
            p0, p1 = guide.get("p0", QtCore.QPointF(0, 300)), guide.get("p1", QtCore.QPointF(800, 300))
            dx, dy = p1.x() - p0.x(), p1.y() - p0.y()
            length = math.hypot(dx, dy) or 1.0
            ux, uy = dx / length, dy / length
            painter.drawLine(QtCore.QPointF(p0.x() - 8000.0 * ux, p0.y() - 8000.0 * uy), QtCore.QPointF(p1.x() + 8000.0 * ux, p1.y() + 8000.0 * uy))
            painter.setBrush(QtGui.QColor(59, 130, 246, 220))
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), line_w))
            painter.drawEllipse(p0, handle_r, handle_r)
            painter.drawEllipse(p1, handle_r, handle_r)

        elif gtype == "curve_ruler":
            p0, p1, p2, p3 = guide.get("p0", QtCore.QPointF(100, 300)), guide.get("p1", QtCore.QPointF(250, 150)), guide.get("p2", QtCore.QPointF(550, 150)), guide.get("p3", QtCore.QPointF(700, 300))
            path = QtGui.QPainterPath()
            path.moveTo(p0)
            path.cubicTo(p1, p2, p3)
            painter.drawPath(path)
            painter.setPen(QtGui.QPen(QtGui.QColor(59, 130, 246, 120), line_w * 0.8, QtCore.Qt.DotLine))
            painter.drawLine(p0, p1)
            painter.drawLine(p3, p2)
            painter.setBrush(QtGui.QColor(59, 130, 246, 220))
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), line_w))
            for pt in (p0, p1, p2, p3): painter.drawEllipse(pt, handle_r, handle_r)

        elif gtype in ("one_point", "two_point", "three_point"):
            GeometryOverlayRenderer._render_perspective(painter, gtype, guide, line_w, handle_r)

        elif gtype == "isometric":
            GeometryOverlayRenderer._render_isometric(painter, line_w)

        elif gtype == "curvilinear":
            GeometryOverlayRenderer._render_curvilinear(painter, guide, line_w, handle_r, zoom_factor)
            if hasattr(ctrl_or_guide, "dynamic_hover_curves") and ctrl_or_guide.dynamic_hover_curves and guide.get("show_hint", True):
                GeometryOverlayRenderer._render_curvilinear_hover(painter, ctrl_or_guide, line_w, handle_r)

        painter.restore()

    @staticmethod
    def _render_perspective(painter: QtGui.QPainter, gtype: str, guide: dict, line_w: float, handle_r: float):
        vps = []
        if gtype in ("one_point", "two_point", "three_point"): vps.append(guide.get("vpA", QtCore.QPointF(400, 300)))
        if gtype in ("two_point", "three_point"): vps.append(guide.get("vpB", QtCore.QPointF(-600, 300)))
        if gtype == "three_point": vps.append(guide.get("vpC", QtCore.QPointF(400, -1200)))

        if len(vps) >= 2:
            painter.setPen(QtGui.QPen(QtGui.QColor(234, 88, 12, 180), line_w * 1.5))
            painter.drawLine(QtCore.QPointF(-8000, vps[0].y()), QtCore.QPointF(8000, vps[0].y()))

        for vp in vps:
            painter.setBrush(QtGui.QColor(234, 88, 12, 220))
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), line_w))
            painter.drawEllipse(vp, handle_r * 1.2, handle_r * 1.2)
            painter.setPen(QtGui.QPen(QtGui.QColor(234, 88, 12, 90), line_w, QtCore.Qt.DashLine))
            for deg in range(0, 360, 20):
                rad = math.radians(deg)
                painter.drawLine(vp, QtCore.QPointF(vp.x() + 4000.0 * math.cos(rad), vp.y() + 4000.0 * math.sin(rad)))

    @staticmethod
    def _render_isometric(painter: QtGui.QPainter, line_w: float):
        painter.setPen(QtGui.QPen(QtGui.QColor(59, 130, 246, 75), line_w, QtCore.Qt.DashLine))
        spacing = 80.0
        for i in range(-50, 50):
            y_base = i * spacing
            painter.drawLine(QtCore.QPointF(-4000, y_base - 4000 * math.tan(math.pi / 6)), QtCore.QPointF(4000, y_base + 4000 * math.tan(math.pi / 6)))
            painter.drawLine(QtCore.QPointF(-4000, y_base + 4000 * math.tan(math.pi / 6)), QtCore.QPointF(4000, y_base - 4000 * math.tan(math.pi / 6)))
            painter.drawLine(QtCore.QPointF(i * spacing, -4000), QtCore.QPointF(i * spacing, 4000))

    @staticmethod
    def _render_curvilinear(painter: QtGui.QPainter, guide: dict, line_w: float, handle_r: float, zoom_factor: float):
        cx, cy = guide.get("cx", 400.0), guide.get("cy", 300.0)
        fov_rad = math.radians(guide.get("fov", 130.0))
        tan_f = math.tan(fov_rad / 4.0)
        R = 400.0 / tan_f if tan_f > 1e-5 else 1e5
        density_rad = math.radians(guide.get("density", 30.0))
        yaw_rad, pitch_rad = math.radians(guide.get("yaw", 0.0)), math.radians(guide.get("pitch", 0.0))

        def p3d_to_2d(X, Y, Z):
            xc, yc, zc = rotate_3d_backward(X, Y, Z, yaw_rad, pitch_rad)
            length = math.sqrt(xc * xc + yc * yc + zc * zc) or 1.0
            ux, uy, uz = xc / length, yc / length, zc / length
            if uz >= 0.999: return None
            return QtCore.QPointF(cx + (ux / (1.0 - uz)) * R, cy - (uy / (1.0 - uz)) * R)

        has_ring = guide.get("show_ring", True)
        if has_ring:
            painter.setPen(QtGui.QPen(QtGui.QColor(168, 85, 247, 220), line_w * 1.5))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawEllipse(QtCore.QPointF(cx, cy), R, R)
            clip = QtGui.QPainterPath()
            clip.addEllipse(QtCore.QPointF(cx, cy), R, R)
            painter.save()
            painter.setClipPath(clip)

        # 1. Ground Grid (Y = -1.0)
        if guide.get("show_ground", False):
            painter.setPen(QtGui.QPen(QtGui.QColor(100, 200, 150, 60), line_w, QtCore.Qt.SolidLine))
            ground_path = QtGui.QPainterPath()
            for x_val in range(-10, 11, 2):
                first = True
                for i in range(51):
                    z = -15.0 + i * (30.0 / 50.0)
                    if abs(z - 1.0) < 0.1: continue
                    pt = p3d_to_2d(float(x_val), -1.0, z)
                    if pt:
                        if first: ground_path.moveTo(pt); first = False
                        else: ground_path.lineTo(pt)
            for z_val in range(-10, 11, 2):
                if abs(float(z_val) - 1.0) < 0.05: continue
                first = True
                for i in range(51):
                    x = -15.0 + i * (30.0 / 50.0)
                    pt = p3d_to_2d(x, -1.0, float(z_val))
                    if pt:
                        if first: ground_path.moveTo(pt); first = False
                        else: ground_path.lineTo(pt)
            painter.drawPath(ground_path)

        # 2. Ground Verticals
        if guide.get("show_ground_verticals", False):
            painter.setPen(QtGui.QPen(QtGui.QColor(100, 150, 255, 60), line_w, QtCore.Qt.DashLine))
            straight_v = guide.get("show_straight_verticals", False)
            gv_path = QtGui.QPainterPath()
            for x_val in range(-6, 7, 2):
                for z_val in range(-6, 7, 2):
                    pt_base = p3d_to_2d(float(x_val), -1.0, float(z_val))
                    if pt_base:
                        if straight_v:
                            pt_top = p3d_to_2d(float(x_val), 1.5, float(z_val))
                            if pt_top:
                                gv_path.moveTo(pt_base)
                                gv_path.lineTo(pt_top)
                        else:
                            gv_path.moveTo(pt_base)
                            for i in range(1, 16):
                                y = -1.0 + i * (2.5 / 15.0)
                                pt = p3d_to_2d(float(x_val), y, float(z_val))
                                if pt: gv_path.lineTo(pt)
            painter.drawPath(gv_path)

        # 3. Ceiling Grid (Y = +1.0)
        if guide.get("show_ceiling", False):
            painter.setPen(QtGui.QPen(QtGui.QColor(200, 150, 100, 60), line_w, QtCore.Qt.SolidLine))
            ceil_path = QtGui.QPainterPath()
            for x_val in range(-10, 11, 2):
                first = True
                for i in range(51):
                    z = -15.0 + i * (30.0 / 50.0)
                    if abs(z - 1.0) < 0.1: continue
                    pt = p3d_to_2d(float(x_val), 1.0, z)
                    if pt:
                        if first: ceil_path.moveTo(pt); first = False
                        else: ceil_path.lineTo(pt)
            for z_val in range(-10, 11, 2):
                if abs(float(z_val) - 1.0) < 0.05: continue
                first = True
                for i in range(51):
                    x = -15.0 + i * (30.0 / 50.0)
                    pt = p3d_to_2d(x, 1.0, float(z_val))
                    if pt:
                        if first: ceil_path.moveTo(pt); first = False
                        else: ceil_path.lineTo(pt)
            painter.drawPath(ceil_path)

        # 4. Ceiling Verticals
        if guide.get("show_ceiling_verticals", False):
            painter.setPen(QtGui.QPen(QtGui.QColor(200, 100, 100, 60), line_w, QtCore.Qt.DashLine))
            straight_v = guide.get("show_straight_verticals", False)
            cv_path = QtGui.QPainterPath()
            for x_val in range(-6, 7, 2):
                for z_val in range(-6, 7, 2):
                    pt_base = p3d_to_2d(float(x_val), 1.0, float(z_val))
                    if pt_base:
                        if straight_v:
                            pt_top = p3d_to_2d(float(x_val), -1.5, float(z_val))
                            if pt_top:
                                cv_path.moveTo(pt_base)
                                cv_path.lineTo(pt_top)
                        else:
                            cv_path.moveTo(pt_base)
                            for i in range(1, 16):
                                y = 1.0 - i * (2.5 / 15.0)
                                pt = p3d_to_2d(float(x_val), y, float(z_val))
                                if pt: cv_path.lineTo(pt)
            painter.drawPath(cv_path)

        # 5. 3D Perspective Cube
        if guide.get("show_cube", False):
            painter.setPen(QtGui.QPen(QtGui.QColor(150, 100, 255, 180), line_w * 1.4))
            xm, xp, ym, yp, zm, zp = -0.75, 0.75, -1.0, 0.5, -3.75, -2.25
            edges = [
                ((xm, ym, zm), (xp, ym, zm)), ((xm, yp, zm), (xp, yp, zm)),
                ((xm, ym, zp), (xp, ym, zp)), ((xm, yp, zp), (xp, yp, zp)),
                ((xm, ym, zm), (xm, yp, zm)), ((xp, ym, zm), (xp, yp, zm)),
                ((xm, ym, zp), (xm, yp, zp)), ((xp, ym, zp), (xp, yp, zp)),
                ((xm, ym, zm), (xm, ym, zp)), ((xp, ym, zm), (xp, ym, zp)),
                ((xm, yp, zm), (xm, yp, zp)), ((xp, yp, zm), (xp, yp, zp))
            ]
            for p1, p2 in edges:
                path_edge = QtGui.QPainterPath()
                first = True
                for step in range(11):
                    t = step / 10.0
                    pt = p3d_to_2d(p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]), p1[2] + t * (p2[2] - p1[2]))
                    if pt:
                        if first: path_edge.moveTo(pt); first = False
                        else: path_edge.lineTo(pt)
                painter.drawPath(path_edge)

        # 5. Principal Grid Curves (V, H, D)
        steps = int(math.pi / density_rad) + 1
        if guide.get("show_v", True):
            painter.setPen(QtGui.QPen(QtGui.QColor(90, 140, 255, 110), line_w, QtCore.Qt.DashLine))
            for i in range(steps):
                phi = i * density_rad
                a, b, c = rotate_3d_backward(math.cos(phi), 0.0, math.sin(phi), yaw_rad, pitch_rad)
                curv = create_curve_from_normal(a, b, c, R, cx, cy, "v")
                if curv:
                    if curv["type"] == "line": painter.drawLine(curv["p1"], curv["p2"])
                    else: painter.drawEllipse(curv["center"], curv["radius"], curv["radius"])

        if guide.get("show_h", True):
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 90, 130, 110), line_w, QtCore.Qt.DashLine))
            for i in range(steps):
                theta = -math.pi / 2.0 + i * density_rad
                a, b, c = rotate_3d_backward(0.0, -math.sin(theta), math.cos(theta), yaw_rad, pitch_rad)
                curv = create_curve_from_normal(a, b, c, R, cx, cy, "h")
                if curv:
                    if curv["type"] == "line": painter.drawLine(curv["p1"], curv["p2"])
                    else: painter.drawEllipse(curv["center"], curv["radius"], curv["radius"])

        if guide.get("show_d", True):
            painter.setPen(QtGui.QPen(QtGui.QColor(90, 210, 130, 110), line_w, QtCore.Qt.DashLine))
            for i in range(steps):
                psi = i * density_rad
                a, b, c = rotate_3d_backward(-math.sin(psi), math.cos(psi), 0.0, yaw_rad, pitch_rad)
                curv = create_curve_from_normal(a, b, c, R, cx, cy, "d")
                if curv:
                    if curv["type"] == "line": painter.drawLine(curv["p1"], curv["p2"])
                    else: painter.drawEllipse(curv["center"], curv["radius"], curv["radius"])

        # 6. 6 Vanishing Points (Z, N, L, R, F, B)
        if guide.get("show_vps", False):
            vps = [("Z", (0, 1, 0), QtGui.QColor(90, 140, 255)), ("N", (0, -1, 0), QtGui.QColor(90, 140, 255)),
                   ("L", (-1, 0, 0), QtGui.QColor(255, 90, 130)), ("R", (1, 0, 0), QtGui.QColor(255, 90, 130)),
                   ("F", (0, 0, -1), QtGui.QColor(90, 210, 130)), ("B", (0, 0, 1), QtGui.QColor(180, 180, 180))]
            font = QtGui.QFont("Segoe UI", max(6, int(8 / max(0.01, line_w))), QtGui.QFont.Bold)
            painter.setFont(font)
            for name, (dx, dy, dz), col in vps:
                pt = p3d_to_2d(float(dx), float(dy), float(dz))
                if pt:
                    painter.setBrush(col)
                    painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0), line_w))
                    painter.drawEllipse(pt, handle_r * 0.8, handle_r * 0.8)
                    painter.setPen(QtGui.QPen(col))
                    painter.drawText(int(pt.x() + 6), int(pt.y() + 4), name)

        if has_ring:
            painter.restore()

        # 7. Viewport Letterbox Overlay
        if guide.get("show_letterbox", False):
            ratio = 2.35 if guide.get("aspect_ratio") == "2.35:1" else (16.0 / 9.0)
            box_w = min(1920.0, R * 1.8)
            box_h = box_w / ratio
            x0, y0 = cx - box_w / 2.0, cy - box_h / 2.0
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 120), line_w * 1.5))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(QtCore.QRectF(x0, y0, box_w, box_h))

        # 8. Central Pivot & Interactive Rotation Arm (80px)
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
    def _render_curvilinear_hover(painter: QtGui.QPainter, ctrl, line_w: float, handle_r: float):
        cx, cy = ctrl.guide_state.get("cx", 400.0), ctrl.guide_state.get("cy", 300.0)
        fov_rad = math.radians(ctrl.guide_state.get("fov", 130.0))
        tan_f = math.tan(fov_rad / 4.0)
        R = 400.0 / tan_f if tan_f > 1e-5 else 1e9

        if ctrl.guide_state.get("show_ring", True):
            clip = QtGui.QPainterPath()
            clip.addEllipse(QtCore.QPointF(cx, cy), R, R)
            painter.save()
            painter.setClipPath(clip)

        curves_to_draw = ctrl.dynamic_hover_curves
        mode = ctrl.guide_state.get("snap_mode", "auto")
        if mode in ("v", "h", "d"):
            curves_to_draw = [c for c in curves_to_draw if c.get("family") == mode or c.get("family", "").endswith(f"_{mode}")]

        pen_hint = QtGui.QPen(QtGui.QColor(255, 125, 45, 75), line_w * 1.2, QtCore.Qt.DashLine)
        painter.setPen(pen_hint)
        painter.setBrush(QtCore.Qt.NoBrush)

        for c in curves_to_draw:
            if c["type"] == "line": painter.drawLine(c["p1"], c["p2"])
            else: painter.drawEllipse(c["center"], c["radius"], c["radius"])

        if ctrl.is_stroking and ctrl.locked_curve is not None:
            pen_locked = QtGui.QPen(QtGui.QColor(255, 100, 30, 160), line_w * 1.8, QtCore.Qt.SolidLine)
            painter.setPen(pen_locked)
            painter.setBrush(QtCore.Qt.NoBrush)
            if ctrl.locked_curve["type"] == "line":
                painter.drawLine(ctrl.locked_curve["p1"], ctrl.locked_curve["p2"])
            else:
                painter.drawEllipse(ctrl.locked_curve["center"], ctrl.locked_curve["radius"], ctrl.locked_curve["radius"])

        # Hollow / Vazada target cursor circle with transparent center
        if ctrl.hover_point is not None:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 125, 45, 230), line_w * 1.5))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawEllipse(ctrl.hover_point, handle_r * 1.2, handle_r * 1.2)

        if ctrl.guide_state.get("show_ring", True):
            painter.restore()
