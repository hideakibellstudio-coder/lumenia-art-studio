"""Curvilinear 6P Mesh and Path Builder.

Constructs and caches 3D stereographic fisheye paths, grids, and vanishing points.
Separates analytical geometric generation from painter rendering in compliance with ARCcC v2 (< 220 LOC).
"""

import math
from PySide6 import QtCore, QtGui
from .camera_3d_projector import rotate_3d_backward, create_curve_from_normal


class CurvilinearMeshBuilder:
    """Computes and caches 3D curvilinear fisheye paths and curves."""

    _curv_cache: dict = {}

    @classmethod
    def get_cached_curvilinear_data(cls, guide: dict) -> dict:
        """Computes or retrieves cached 3D curves and paths for curvilinear perspective."""
        cx, cy = float(guide.get("cx", 400.0)), float(guide.get("cy", 300.0))
        fov = float(guide.get("fov", 130.0))
        base_r = float(guide.get("base_radius", 400.0))
        density = float(guide.get("density", 30.0))
        yaw = round(float(guide.get("yaw", 0.0)), 2)
        pitch = round(float(guide.get("pitch", 0.0)), 2)

        cache_key = (
            cx, cy, fov, base_r, density, yaw, pitch,
            bool(guide.get("show_v", True)),
            bool(guide.get("show_h", True)),
            bool(guide.get("show_d", True)),
            bool(guide.get("show_ground", False)),
            bool(guide.get("show_ceiling", False)),
            bool(guide.get("show_ground_verticals", False)),
            bool(guide.get("show_ceiling_verticals", False)),
            bool(guide.get("show_straight_verticals", False)),
            bool(guide.get("show_cube", False)),
            bool(guide.get("show_vps", False)),
            bool(guide.get("show_letterbox", False)),
            str(guide.get("aspect_ratio", "16:9"))
        )

        if cache_key in cls._curv_cache:
            return cls._curv_cache[cache_key]

        fov_rad = math.radians(fov)
        tan_f = math.tan(fov_rad / 4.0)
        R = base_r / tan_f if tan_f > 1e-5 else 1e5
        density_rad = math.radians(density)
        yaw_rad, pitch_rad = math.radians(yaw), math.radians(pitch)

        def p3d_to_2d(X, Y, Z):
            xc, yc, zc = rotate_3d_backward(X, Y, Z, yaw_rad, pitch_rad)
            length = math.sqrt(xc * xc + yc * yc + zc * zc) or 1.0
            ux, uy, uz = xc / length, yc / length, zc / length
            if uz >= 0.999:
                return None
            return QtCore.QPointF(cx + (ux / (1.0 - uz)) * R, cy - (uy / (1.0 - uz)) * R)

        data = {
            "cx": cx, "cy": cy, "R": R,
            "yaw_rad": yaw_rad, "pitch_rad": pitch_rad,
            "v_curves": [], "h_curves": [], "d_curves": [],
            "ground_path": QtGui.QPainterPath(),
            "ceiling_path": QtGui.QPainterPath(),
            "gv_path": QtGui.QPainterPath(),
            "cv_path": QtGui.QPainterPath(),
            "cube_path": QtGui.QPainterPath(),
            "vps": [],
            "letterbox_rect": None
        }

        # 1. Ground Grid (Y = -1.0)
        if guide.get("show_ground", False):
            for x_val in range(-10, 11, 2):
                first = True
                for step in range(31):
                    z = -15.0 + step * (30.0 / 30.0)
                    pt = p3d_to_2d(float(x_val), -1.0, z)
                    if pt:
                        if first:
                            data["ground_path"].moveTo(pt)
                            first = False
                        else:
                            data["ground_path"].lineTo(pt)
            for z_val in range(-10, 11, 2):
                first = True
                for step in range(31):
                    x = -15.0 + step * (30.0 / 30.0)
                    pt = p3d_to_2d(x, -1.0, float(z_val))
                    if pt:
                        if first:
                            data["ground_path"].moveTo(pt)
                            first = False
                        else:
                            data["ground_path"].lineTo(pt)

        # 2. Ground Verticals
        if guide.get("show_ground_verticals", False):
            straight_v = guide.get("show_straight_verticals", False)
            for x_val in range(-6, 7, 2):
                for z_val in range(-6, 7, 2):
                    pt_base = p3d_to_2d(float(x_val), -1.0, float(z_val))
                    if pt_base:
                        data["gv_path"].moveTo(pt_base)
                        if straight_v:
                            pt_top = p3d_to_2d(float(x_val), 1.5, float(z_val))
                            if pt_top:
                                data["gv_path"].lineTo(pt_top)
                        else:
                            for i in range(1, 16):
                                y = -1.0 + i * (2.5 / 15.0)
                                pt = p3d_to_2d(float(x_val), y, float(z_val))
                                if pt:
                                    data["gv_path"].lineTo(pt)

        # 3. Ceiling Grid (Y = +1.0)
        if guide.get("show_ceiling", False):
            for x_val in range(-10, 11, 2):
                first = True
                for step in range(31):
                    z = -15.0 + step * (30.0 / 30.0)
                    pt = p3d_to_2d(float(x_val), 1.0, z)
                    if pt:
                        if first:
                            data["ceiling_path"].moveTo(pt)
                            first = False
                        else:
                            data["ceiling_path"].lineTo(pt)
            for z_val in range(-10, 11, 2):
                first = True
                for step in range(31):
                    x = -15.0 + step * (30.0 / 30.0)
                    pt = p3d_to_2d(x, 1.0, float(z_val))
                    if pt:
                        if first:
                            data["ceiling_path"].moveTo(pt)
                            first = False
                        else:
                            data["ceiling_path"].lineTo(pt)

        # 4. Ceiling Verticals
        if guide.get("show_ceiling_verticals", False):
            straight_v = guide.get("show_straight_verticals", False)
            for x_val in range(-6, 7, 2):
                for z_val in range(-6, 7, 2):
                    pt_base = p3d_to_2d(float(x_val), 1.0, float(z_val))
                    if pt_base:
                        data["cv_path"].moveTo(pt_base)
                        if straight_v:
                            pt_top = p3d_to_2d(float(x_val), -1.5, float(z_val))
                            if pt_top:
                                data["cv_path"].lineTo(pt_top)
                        else:
                            for i in range(1, 16):
                                y = 1.0 - i * (2.5 / 15.0)
                                pt = p3d_to_2d(float(x_val), y, float(z_val))
                                if pt:
                                    data["cv_path"].lineTo(pt)

        # 5. 3D Perspective Cube
        if guide.get("show_cube", False):
            xm, xp, ym, yp, zm, zp = -0.75, 0.75, -1.0, 0.5, -3.75, -2.25
            edges = [
                ((xm, ym, zm), (xp, ym, zm)), ((xm, yp, zm), (xp, yp, zm)),
                ((xm, ym, zp), (xp, ym, zp)), ((xm, yp, zp), (xp, yp, zp)),
                ((xm, ym, zm), (xm, yp, zm)), ((xp, ym, zm), (xp, yp, zm)),
                ((xm, ym, zp), (xp, ym, zp)), ((xp, yp, zp), (xp, yp, zp)),
                ((xm, ym, zm), (xm, ym, zp)), ((xp, ym, zm), (xp, yp, zp)),
                ((xm, yp, zm), (xm, yp, zp)), ((xm, yp, zm), (xp, yp, zp))
            ]
            for p1, p2 in edges:
                first = True
                for step in range(11):
                    t = step / 10.0
                    pt = p3d_to_2d(p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]), p1[2] + t * (p2[2] - p1[2]))
                    if pt:
                        if first:
                            data["cube_path"].moveTo(pt)
                            first = False
                        else:
                            data["cube_path"].lineTo(pt)

        # 6. Principal Grid Curves (V, H, D)
        steps = int(math.pi / density_rad) + 1
        if guide.get("show_v", True):
            for i in range(steps):
                phi = i * density_rad
                a, b, c = rotate_3d_backward(math.cos(phi), 0.0, math.sin(phi), yaw_rad, pitch_rad)
                curv = create_curve_from_normal(a, b, c, R, cx, cy, "v")
                if curv:
                    data["v_curves"].append(curv)

        if guide.get("show_h", True):
            for i in range(steps):
                theta = -math.pi / 2.0 + i * density_rad
                a, b, c = rotate_3d_backward(0.0, -math.sin(theta), math.cos(theta), yaw_rad, pitch_rad)
                curv = create_curve_from_normal(a, b, c, R, cx, cy, "h")
                if curv:
                    data["h_curves"].append(curv)

        if guide.get("show_d", True):
            for i in range(steps):
                psi = i * density_rad
                a, b, c = rotate_3d_backward(-math.sin(psi), math.cos(psi), 0.0, yaw_rad, pitch_rad)
                curv = create_curve_from_normal(a, b, c, R, cx, cy, "d")
                if curv:
                    data["d_curves"].append(curv)

        # 7. 6 Vanishing Points (Z, N, L, R, F, B)
        if guide.get("show_vps", False):
            vps_def = [
                ("Z", (0, 1, 0), QtGui.QColor(90, 140, 255)),
                ("N", (0, -1, 0), QtGui.QColor(90, 140, 255)),
                ("L", (-1, 0, 0), QtGui.QColor(255, 90, 130)),
                ("R", (1, 0, 0), QtGui.QColor(255, 90, 130)),
                ("F", (0, 0, -1), QtGui.QColor(90, 210, 130)),
                ("B", (0, 0, 1), QtGui.QColor(180, 180, 180))
            ]
            for name, (dx, dy, dz), col in vps_def:
                pt = p3d_to_2d(float(dx), float(dy), float(dz))
                if pt:
                    data["vps"].append((name, pt, col))

        # 8. Viewport Letterbox Overlay
        if guide.get("show_letterbox", False):
            ratio = 2.35 if guide.get("aspect_ratio") == "2.35:1" else (16.0 / 9.0)
            box_w = min(1920.0, R * 1.8)
            box_h = box_w / ratio
            data["letterbox_rect"] = QtCore.QRectF(cx - box_w / 2.0, cy - box_h / 2.0, box_w, box_h)

        if len(cls._curv_cache) > 8:
            cls._curv_cache.clear()
        cls._curv_cache[cache_key] = data
        return data
