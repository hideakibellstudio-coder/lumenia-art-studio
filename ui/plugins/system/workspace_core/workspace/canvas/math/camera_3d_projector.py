"""Pure 3D mathematical projection and transformation utilities.

Decoupled from Qt GUI widgets and painters in compliance with ARCcC v2.
Handles 3D camera rotations, fisheye curvilinear stereographic projection,
conic curve creation, and closest-point curve snapping calculations.
"""

import math
from PySide6 import QtCore


def rotate_3d_forward(x: float, y: float, z: float, yaw_rad: float, pitch_rad: float) -> tuple[float, float, float]:
    """Applies camera pitch and yaw rotations in forward direction."""
    ch, sh = math.cos(yaw_rad), math.sin(yaw_rad)
    cv, sv = math.cos(pitch_rad), math.sin(pitch_rad)
    xr = x * ch - z * sh
    yr = y
    zr = x * sh + z * ch
    return xr, yr * cv - zr * sv, yr * sv + zr * cv


def rotate_3d_backward(x: float, y: float, z: float, yaw_rad: float, pitch_rad: float) -> tuple[float, float, float]:
    """Applies camera pitch and yaw rotations in reverse (unproject) direction."""
    ch, sh = math.cos(yaw_rad), math.sin(yaw_rad)
    cv, sv = math.cos(pitch_rad), math.sin(pitch_rad)
    xu = x
    yu = y * cv + z * sv
    zu = -y * sv + z * cv
    x_unrot = xu * ch + zu * sh
    y_unrot = yu
    z_unrot = -xu * sh + zu * ch
    return x_unrot, y_unrot, z_unrot


def get_curvilinear_camera_radius(fov: float, base_r: float) -> float:
    """Computes stereographic projection sphere radius R from FOV and base radius."""
    fov_rad = math.radians(fov)
    tan_f = math.tan(fov_rad / 4.0)
    return base_r / tan_f if tan_f > 1e-5 else 1e9


def p3d_to_2d_fisheye(
    X: float,
    Y: float,
    Z: float,
    yaw_rad: float,
    pitch_rad: float,
    cx: float,
    cy: float,
    R: float
) -> QtCore.QPointF | None:
    """Projects 3D world coordinates into 2D stereographic fisheye canvas coordinates."""
    xc, yc, zc = rotate_3d_backward(X, Y, Z, yaw_rad, pitch_rad)
    length = math.sqrt(xc * xc + yc * yc + zc * zc) or 1.0
    ux, uy, uz = xc / length, yc / length, zc / length
    if uz >= 0.999:
        return None
    denom = 1.0 - uz
    return QtCore.QPointF(cx + (ux / denom) * R, cy - (uy / denom) * R)


def create_curve_from_normal(
    a: float,
    b: float,
    c: float,
    R: float,
    cx: float,
    cy: float,
    family: str
) -> dict | None:
    """Computes intersection curve (circle or straight line) of a plane normal with stereographic sphere."""
    norm = math.sqrt(a * a + b * b + c * c)
    if norm > 1e-6:
        a, b, c = a / norm, b / norm, c / norm
    else:
        return None

    if abs(c) < 1e-6:
        denom = math.sqrt(a * a + b * b)
        if denom < 1e-6:
            return None
        dx, dy = b / denom, a / denom
        return {
            "type": "line",
            "family": family,
            "p1": QtCore.QPointF(cx - dx * 100000.0, cy - dy * 100000.0),
            "p2": QtCore.QPointF(cx + dx * 100000.0, cy + dy * 100000.0),
            "dir": QtCore.QPointF(dx, dy)
        }
    else:
        cx_c, cy_c, radius = -R * a / c, R * b / c, R / abs(c)
        return {
            "type": "circle",
            "family": family,
            "center": QtCore.QPointF(cx + cx_c, cy + cy_c),
            "radius": radius
        }


def closest_point_on_curve(curve: dict, pt: QtCore.QPointF) -> QtCore.QPointF:
    """Finds the closest point on an analytical curve (line, polyline, or circle)."""
    ctype = curve.get("type", "circle")
    if ctype == "line":
        p1, p2 = curve["p1"], curve["p2"]
        v = p2 - p1
        len2 = v.x() * v.x() + v.y() * v.y()
        if len2 < 1e-6:
            return p1
        t = ((pt.x() - p1.x()) * v.x() + (pt.y() - p1.y()) * v.y()) / len2
        return QtCore.QPointF(p1.x() + t * v.x(), p1.y() + t * v.y())

    if ctype == "polyline":
        pts = curve.get("points", [])
        if not pts:
            return pt
        best_pt, best_d2 = pts[0], float("inf")
        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i + 1]
            vx, vy = p2.x() - p1.x(), p2.y() - p1.y()
            len2 = vx * vx + vy * vy
            t = 0.0 if len2 < 1e-6 else max(0.0, min(1.0, ((pt.x() - p1.x()) * vx + (pt.y() - p1.y()) * vy) / len2))
            cand = QtCore.QPointF(p1.x() + t * vx, p1.y() + t * vy)
            d2 = (cand.x() - pt.x()) * (cand.x() - pt.x()) + (cand.y() - pt.y()) * (cand.y() - pt.y())
            if d2 < best_d2:
                best_d2, best_pt = d2, cand
        return best_pt

    center, radius = curve["center"], curve["radius"]
    dx, dy = pt.x() - center.x(), pt.y() - center.y()
    dist = math.hypot(dx, dy)
    if dist > 1e-5:
        return QtCore.QPointF(center.x() + (dx / dist) * radius, center.y() + (dy / dist) * radius)
    return QtCore.QPointF(center.x() + radius, center.y())
