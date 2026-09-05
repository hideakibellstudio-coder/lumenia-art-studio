"""Pure Analytical Geometry Snapping Engine.

Computes point projection, tangent scoring, and magnetic attraction
for straight rulers (parallel offset), Bézier curves, ray perspectives (1P/2P/3P/Isometric),
and 6P curvilinear fisheye guides.
Strictly decoupled in compliance with ARCcC v2 (< 250 LOC).
"""

import math
from PySide6 import QtCore
from ..math.camera_3d_projector import (
    rotate_3d_forward,
    rotate_3d_backward,
    create_curve_from_normal,
    closest_point_on_curve,
    get_curvilinear_camera_radius
)


class GeometrySnappingEngine:
    """Analytical mathematical engine for stylus snapping calculations."""

    @staticmethod
    def snap_straight(
        raw_x: float,
        raw_y: float,
        zoom: float,
        guide_state: dict,
        is_stroking: bool,
        start_distance: tuple[float, float]
    ) -> tuple[float, float]:
        """Snaps a point to a straight ruler with parallel contact offset tracking."""
        p0, p1 = guide_state["p0"], guide_state["p1"]
        dx, dy = p1.x() - p0.x(), p1.y() - p0.y()
        len2 = dx * dx + dy * dy
        if len2 > 1e-6:
            t = ((raw_x - p0.x()) * dx + (raw_y - p0.y()) * dy) / len2
            proj_x, proj_y = p0.x() + t * dx, p0.y() + t * dy
            if not is_stroking:
                eff_r = guide_state.get("snap_radius", 32.0) / max(0.01, float(zoom))
                d2 = (raw_x - proj_x) ** 2 + (raw_y - proj_y) ** 2
                if d2 > eff_r * eff_r:
                    return (raw_x, raw_y)
            return (proj_x + start_distance[0], proj_y + start_distance[1])
        return (p0.x() + start_distance[0], p0.y() + start_distance[1])

    @staticmethod
    def snap_bezier(raw_x: float, raw_y: float, guide_state: dict) -> tuple[float, float]:
        """Snaps a point to a 4-point cubic Bézier guide curve using coarse search + Newton-Raphson."""
        p0, p1, p2, p3 = guide_state["p0"], guide_state["p1"], guide_state["p2"], guide_state["p3"]
        best_t, best_d2 = 0.0, float("inf")
        for i in range(17):
            t, u = i / 16.0, 1.0 - (i / 16.0)
            bx = u**3 * p0.x() + 3 * u**2 * t * p1.x() + 3 * u * t**2 * p2.x() + t**3 * p3.x()
            by = u**3 * p0.y() + 3 * u**2 * t * p1.y() + 3 * u * t**2 * p2.y() + t**3 * p3.y()
            d2 = (bx - raw_x) ** 2 + (by - raw_y) ** 2
            if d2 < best_d2:
                best_d2, best_t = d2, t
        t = best_t
        for _ in range(4):
            u = 1.0 - t
            bx = u**3 * p0.x() + 3 * u**2 * t * p1.x() + 3 * u * t**2 * p2.x() + t**3 * p3.x()
            by = u**3 * p0.y() + 3 * u**2 * t * p1.y() + 3 * u * t**2 * p2.y() + t**3 * p3.y()
            dpx = 3 * (u**2 * (p1.x() - p0.x()) + 2 * u * t * (p2.x() - p1.x()) + t**2 * (p3.x() - p2.x()))
            dpy = 3 * (u**2 * (p1.y() - p0.y()) + 2 * u * t * (p2.y() - p1.y()) + t**2 * (p3.y() - p2.y()))
            fp = dpx * dpx + dpy * dpy
            if abs(fp) > 1e-6:
                t = max(0.0, min(1.0, t - ((bx - raw_x) * dpx + (by - raw_y) * dpy) / fp))
        u = 1.0 - t
        return (
            u**3 * p0.x() + 3 * u**2 * t * p1.x() + 3 * u * t**2 * p2.x() + t**3 * p3.x(),
            u**3 * p0.y() + 3 * u**2 * t * p1.y() + 3 * u * t**2 * p2.y() + t**3 * p3.y()
        )

    @staticmethod
    def snap_ray_perspective(
        raw_x: float,
        raw_y: float,
        zoom: float,
        guide_state: dict,
        snap_start_pt: QtCore.QPointF,
        locked_dir: tuple[float, float] | None
    ) -> tuple[tuple[float, float], tuple[float, float] | None]:
        """Snaps to origin rays of linear perspective (1P, 2P, 3P, Isometric)."""
        gtype = guide_state["type"]
        start = snap_start_pt or QtCore.QPointF(raw_x, raw_y)

        if locked_dir is not None:
            t = (raw_x - start.x()) * locked_dir[0] + (raw_y - start.y()) * locked_dir[1]
            return ((start.x() + t * locked_dir[0], start.y() + t * locked_dir[1]), locked_dir)

        dx, dy = raw_x - start.x(), raw_y - start.y()
        dist = math.hypot(dx, dy)
        if dist < (2.5 / max(0.01, zoom)):
            return ((start.x(), start.y()), None)

        ux, uy = dx / dist, dy / dist
        candidates = []

        if gtype == "one_point":
            vpA = guide_state["vpA"]
            lA = math.hypot(vpA.x() - start.x(), vpA.y() - start.y()) or 1.0
            candidates.extend([((vpA.x() - start.x()) / lA, (vpA.y() - start.y()) / lA), (1.0, 0.0), (0.0, 1.0)])
        elif gtype == "two_point":
            vpA, vpB = guide_state["vpA"], guide_state["vpB"]
            lA = math.hypot(vpA.x() - start.x(), vpA.y() - start.y()) or 1.0
            lB = math.hypot(vpB.x() - start.x(), vpB.y() - start.y()) or 1.0
            candidates.extend([((vpA.x() - start.x()) / lA, (vpA.y() - start.y()) / lA), ((vpB.x() - start.x()) / lB, (vpB.y() - start.y()) / lB)])
            hdx, hdy = vpB.x() - vpA.x(), vpB.y() - vpA.y()
            hlen = math.hypot(hdx, hdy) or 1.0
            candidates.append((-hdy / hlen, hdx / hlen))
        elif gtype == "three_point":
            for n in ("vpA", "vpB", "vpC"):
                l = math.hypot(guide_state[n].x() - start.x(), guide_state[n].y() - start.y()) or 1.0
                candidates.append(((guide_state[n].x() - start.x()) / l, (guide_state[n].y() - start.y()) / l))
        elif gtype == "isometric":
            cos_30 = math.cos(math.pi / 6)
            sin_30 = math.sin(math.pi / 6)
            candidates = [(0.0, 1.0), (cos_30, sin_30), (-cos_30, sin_30)]

        best_dir, max_dot = (1.0, 0.0), -1.0
        for c in candidates:
            dot = abs(c[0] * ux + c[1] * uy)
            if dot > max_dot:
                max_dot, best_dir = dot, c

        t = (raw_x - start.x()) * best_dir[0] + (raw_y - start.y()) * best_dir[1]
        return ((start.x() + t * best_dir[0], start.y() + t * best_dir[1]), best_dir)

    @staticmethod
    def snap_curvilinear(
        raw_x: float,
        raw_y: float,
        zoom: float,
        guide_state: dict,
        snap_start_pt: QtCore.QPointF,
        locked_curve: dict | None,
        candidate_curves: list,
        is_stroking: bool
    ) -> tuple[tuple[float, float], dict | None]:
        """Snaps to dynamic 6P curvilinear curves with gesture direction scoring."""
        pt = QtCore.QPointF(raw_x, raw_y)
        start = snap_start_pt or pt

        if locked_curve is not None:
            snapped = closest_point_on_curve(locked_curve, pt)
            return ((snapped.x(), snapped.y()), locked_curve)

        dx, dy = raw_x - start.x(), raw_y - start.y()
        dist = math.hypot(dx, dy)

        curves = candidate_curves
        mode = guide_state.get("snap_mode", "auto")
        if mode in ("v", "h", "d"):
            curves = [c for c in curves if c.get("family") == mode or c.get("family", "").endswith(f"_{mode}")]

        if not curves:
            return ((raw_x, raw_y), None)

        if mode in ("v", "h", "d") and is_stroking:
            lock = curves[0]
            snapped = closest_point_on_curve(lock, pt)
            return ((snapped.x(), snapped.y()), lock)

        sens = guide_state.get("snap_sensitivity", 3.0)
        lock_thresh = max(2.0, (7.5 - sens * 1.2)) / max(0.01, zoom)

        if dist < lock_thresh:
            best_curve, best_dist = curves[0], float("inf")
            for c in curves:
                cp = closest_point_on_curve(c, pt)
                d = math.hypot(pt.x() - cp.x(), pt.y() - cp.y())
                if d < best_dist:
                    best_dist, best_curve = d, c
            snapped = closest_point_on_curve(best_curve, pt)
            return ((snapped.x(), snapped.y()), None)

        ux, uy = dx / dist, dy / dist
        best_curve, best_score = curves[0], -1.0
        for c in curves:
            cp = closest_point_on_curve(c, pt)
            if c["type"] == "line":
                tdx, tdy = c["dir"].x(), c["dir"].y()
            elif c["type"] == "circle":
                cdx, cdy = cp.x() - c["center"].x(), cp.y() - c["center"].y()
                clen = math.hypot(cdx, cdy) or 1.0
                tdx, tdy = -cdy / clen, cdx / clen
            else:
                tdx, tdy = 1.0, 0.0
            dot = abs(ux * tdx + uy * tdy)
            d = math.hypot(pt.x() - cp.x(), pt.y() - cp.y())
            score = dot / max(1.0, d * 0.05)
            if score > best_score:
                best_score, best_curve = score, c

        if best_curve is not None:
            new_lock = best_curve if is_stroking else None
            snapped = closest_point_on_curve(best_curve, pt)
            return ((snapped.x(), snapped.y()), new_lock)

        return ((raw_x, raw_y), None)

    @classmethod
    def get_dynamic_curves_at_point(cls, guide_state: dict, click_pt: QtCore.QPointF) -> list:
        """Computes orthogonal curvilinear 3D curves passing through a 2D canvas point."""
        cx, cy = guide_state["cx"], guide_state["cy"]
        R = get_curvilinear_camera_radius(guide_state.get("fov", 130.0), guide_state.get("base_radius", 400.0))

        X, Y = (click_pt.x() - cx) / R, -(click_pt.y() - cy) / R
        r2 = X * X + Y * Y
        denom = r2 + 1.0
        x3, y3, z3 = 2.0 * X / denom, 2.0 * Y / denom, (r2 - 1.0) / denom

        yaw_rad = math.radians(guide_state.get("yaw", 0.0))
        pitch_rad = math.radians(guide_state.get("pitch", 0.0))
        xw, yw, zw = rotate_3d_forward(x3, y3, z3, yaw_rad, pitch_rad)

        curves = []

        # 1. Vertical Curve (V)
        if (guide_state.get("show_v", True) or guide_state.get("show_ground_verticals", False) or
                guide_state.get("show_ceiling_verticals", False) or guide_state.get("show_straight_verticals", False)):
            a_v, b_v, c_v = rotate_3d_backward(zw, 0.0, -xw, yaw_rad, pitch_rad)
            if guide_state.get("show_straight_verticals", False):
                Tx, Ty, Tz = b_v * z3 - c_v * y3, c_v * x3 - a_v * z3, a_v * y3 - b_v * x3
                dz = 1.0 - z3
                dx, dy = (Tx * dz + x3 * Tz), -(Ty * dz + y3 * Tz)
                l = math.hypot(dx, dy) or 1.0
                dx, dy = dx / l, dy / l
                curves.append({
                    "type": "line", "family": "ground_v",
                    "p1": QtCore.QPointF(click_pt.x() - dx * 20000.0, click_pt.y() - dy * 20000.0),
                    "p2": QtCore.QPointF(click_pt.x() + dx * 20000.0, click_pt.y() + dy * 20000.0),
                    "dir": QtCore.QPointF(dx, dy)
                })
            else:
                c_v = create_curve_from_normal(a_v, b_v, c_v, R, cx, cy, "ground_v")
                if c_v:
                    curves.append(c_v)

        # 2. Transversal Curve (H)
        if guide_state.get("show_h", True) or guide_state.get("show_ground", False) or guide_state.get("show_ceiling", False):
            a_h, b_h, c_h = rotate_3d_backward(0.0, -zw, yw, yaw_rad, pitch_rad)
            c_h = create_curve_from_normal(a_h, b_h, c_h, R, cx, cy, "ground_x")
            if c_h:
                curves.append(c_h)

        # 3. Depth Curve (D)
        if guide_state.get("show_d", True) or guide_state.get("show_ground", False) or guide_state.get("show_ceiling", False):
            a_d, b_d, c_d = rotate_3d_backward(-yw, xw, 0.0, yaw_rad, pitch_rad)
            c_d = create_curve_from_normal(a_d, b_d, c_d, R, cx, cy, "ground_z")
            if c_d:
                curves.append(c_d)

        return curves

    @classmethod
    def find_nearest_primary_grid_curve(cls, guide_state: dict, pt: QtCore.QPointF, max_dist: float = 24.0) -> dict | None:
        """Finds the closest primary grid curve (meridian/parallel) near a given point."""
        cx, cy = guide_state["cx"], guide_state["cy"]
        R = get_curvilinear_camera_radius(guide_state.get("fov", 130.0), guide_state.get("base_radius", 400.0))
        d_rad = math.radians(guide_state.get("density", 30.0))
        y_rad = math.radians(guide_state.get("yaw", 0.0))
        p_rad = math.radians(guide_state.get("pitch", 0.0))
        steps, p_curves = int(math.pi / d_rad) + 1, []

        if guide_state.get("show_v", True):
            for i in range(steps):
                a, b, c = rotate_3d_backward(math.cos(i * d_rad), 0.0, math.sin(i * d_rad), y_rad, p_rad)
                cv = create_curve_from_normal(a, b, c, R, cx, cy, "ground_v")
                if cv:
                    p_curves.append(cv)

        if guide_state.get("show_h", True):
            for i in range(steps):
                a, b, c = rotate_3d_backward(0.0, -math.sin(-math.pi / 2.0 + i * d_rad), math.cos(-math.pi / 2.0 + i * d_rad), y_rad, p_rad)
                cv = create_curve_from_normal(a, b, c, R, cx, cy, "ground_x")
                if cv:
                    p_curves.append(cv)

        if guide_state.get("show_d", True):
            for i in range(steps):
                a, b, c = rotate_3d_backward(-math.sin(i * d_rad), math.cos(i * d_rad), 0.0, y_rad, p_rad)
                cv = create_curve_from_normal(a, b, c, R, cx, cy, "ground_z")
                if cv:
                    p_curves.append(cv)

        best_c, best_d = None, max_dist
        for c in p_curves:
            cp = closest_point_on_curve(c, pt)
            d = math.hypot(pt.x() - cp.x(), pt.y() - cp.y())
            if d < best_d:
                best_d, best_c = d, c
        return best_c
