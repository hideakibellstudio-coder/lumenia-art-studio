"""Tool Controller for Snapping, Dynamic Perspective and Interactive Handles.

Implements full 3D camera synchronicity with Infinite Painter's parallel offset
and continuous multi-axis adaptive snapping for high-frequency tablet styluses.
"""

import math
from PySide6 import QtCore
from ui.core.engine.registry import EngineRegistry


class GeometryToolController:
    """Unified controller for symmetry, rulers and 6P curvilinear perspective."""

    def __init__(self, widget):
        self.widget = widget
        self.active_handle = None
        self.curv_drag_rotate = False
        self.curv_rotate_start = QtCore.QPointF()
        self.curv_start_angles = (0.0, 0.0)

        # Real-time cursor hint and hover tracking
        self.hover_point = None
        self.dynamic_hover_curves = []

        # Per-stroke snapping state
        self.is_stroking = False
        self.snap_start_pt = None
        self.start_distance = (0.0, 0.0)
        self.locked_curve = None
        self.locked_dir = None
        self.current_stroke_pts = []

        self.sym_state = {
            "mode": "none", "cx": 400.0, "cy": 300.0, "angle": 90.0,
            "segments": 6, "stop_at_center": False, "locked": False,
            "hidden": False, "snap_increment": 15
        }

        self.guide_state = {
            "type": "none",
            "p0": QtCore.QPointF(100, 300), "p1": QtCore.QPointF(700, 300),
            "p2": QtCore.QPointF(300, 150), "p3": QtCore.QPointF(500, 450),
            "vpA": QtCore.QPointF(100, 300), "vpB": QtCore.QPointF(700, 300),
            "vpC": QtCore.QPointF(400, 50),
            "cx": 400.0, "cy": 300.0, "base_radius": 350.0,
            "yaw": 0.0, "pitch": 0.0, "fov": 130.0, "density": 30.0,
            "show_ring": True, "show_v": True, "show_h": True, "show_d": True,
            "show_vps": False, "show_cube": False, "show_ground": False, "show_ground_verticals": False,
            "show_ceiling": False, "show_ceiling_verticals": False, "show_straight_verticals": False,
            "show_letterbox": False, "aspect_ratio": "16:9", "snap_mode": "auto",
            "hidden": False, "snap_radius": 32.0, "snap_dynamic": True, "show_hint": True,
            "snap_sensitivity": 3.0
        }

    def center_on_document(self, doc_w: float, doc_h: float):
        doc_w = max(1.0, float(doc_w))
        doc_h = max(1.0, float(doc_h))
        cx, cy = doc_w / 2.0, doc_h / 2.0
        base_r = min(doc_w, doc_h) * 0.42

        if not getattr(self, "_custom_sym_center", False):
            self.sym_state["cx"], self.sym_state["cy"] = cx, cy

        self.guide_state["cx"], self.guide_state["cy"] = cx, cy
        self.guide_state["base_radius"] = base_r
        self.guide_state["p0"] = QtCore.QPointF(cx - doc_w * 0.35, cy)
        self.guide_state["p1"] = QtCore.QPointF(cx + doc_w * 0.35, cy)
        self.guide_state["p2"] = QtCore.QPointF(cx - doc_w * 0.15, cy - doc_h * 0.18)
        self.guide_state["p3"] = QtCore.QPointF(cx + doc_w * 0.15, cy - doc_h * 0.18)
        self.guide_state["vpA"] = QtCore.QPointF(cx - doc_w * 0.55, cy)
        self.guide_state["vpB"] = QtCore.QPointF(cx + doc_w * 0.55, cy)
        self.guide_state["vpC"] = QtCore.QPointF(cx, cy - doc_h * 0.65)
        self.sync_symmetry_to_engine()
        self.sync_guides_to_engine()

    def handle_hover(self, doc_pt: QtCore.QPointF):
        self.hover_point = doc_pt
        gtype = self.guide_state["type"]
        if gtype == "curvilinear" and self.guide_state.get("show_hint", True):
            self.dynamic_hover_curves = self._get_dynamic_curves_at_point(doc_pt)
        elif not self.is_stroking:
            self.dynamic_hover_curves = []

    def hit_test(self, pos: QtCore.QPointF, zoom: float) -> str | None:
        tol = 16.0 / max(0.01, zoom)
        if self.sym_state["mode"] != "none" and not self.sym_state["locked"] and not self.sym_state["hidden"]:
            cx, cy = self.sym_state["cx"], self.sym_state["cy"]
            if math.hypot(pos.x() - cx, pos.y() - cy) <= tol: return "sym_center"
            rad = math.radians(self.sym_state["angle"])
            dist = 80.0 / max(0.01, zoom)
            if math.hypot(pos.x() - (cx + dist * math.cos(rad)), pos.y() - (cy + dist * math.sin(rad))) <= tol:
                return "sym_angle"

        gtype = self.guide_state["type"]
        if gtype == "straight":
            for n in ("p0", "p1"):
                if math.hypot(pos.x() - self.guide_state[n].x(), pos.y() - self.guide_state[n].y()) <= tol: return f"guide_{n}"
        elif gtype == "curve_ruler":
            for n in ("p0", "p1", "p2", "p3"):
                if math.hypot(pos.x() - self.guide_state[n].x(), pos.y() - self.guide_state[n].y()) <= tol: return f"guide_{n}"
        elif gtype in ("one_point", "two_point", "three_point"):
            for n in ("vpA", "vpB", "vpC"):
                if n in self.guide_state and math.hypot(pos.x() - self.guide_state[n].x(), pos.y() - self.guide_state[n].y()) <= tol:
                    return f"guide_{n}"
        elif gtype == "curvilinear":
            cx, cy = self.guide_state["cx"], self.guide_state["cy"]
            if math.hypot(pos.x() - cx, pos.y() - cy) <= tol: return "guide_curv_center"
            yaw_rad = math.radians(self.guide_state["yaw"])
            hx, hy = cx + (80.0 / max(0.01, zoom)) * math.cos(yaw_rad), cy + (80.0 / max(0.01, zoom)) * math.sin(yaw_rad)
            if math.hypot(pos.x() - hx, pos.y() - hy) <= tol: return "guide_curv_rotate"
        return None

    def mouse_press(self, pos: QtCore.QPointF, zoom: float, is_right: bool = False) -> bool:
        if is_right and self.guide_state["type"] == "curvilinear":
            self.curv_drag_rotate = True
            self.curv_rotate_start = pos
            self.curv_start_angles = (self.guide_state["yaw"], self.guide_state["pitch"])
            return True
        handle = self.hit_test(pos, zoom)
        if handle:
            self.active_handle = handle
            return True
        return False

    def mouse_move(self, pos: QtCore.QPointF, shift_pressed: bool = False) -> bool:
        if self.curv_drag_rotate:
            dx, dy = pos.x() - self.curv_rotate_start.x(), pos.y() - self.curv_rotate_start.y()
            start_yaw, start_pitch = self.curv_start_angles
            self.guide_state["yaw"] = (start_yaw - dx * 0.25) % 360.0
            self.guide_state["pitch"] = max(-90.0, min(90.0, start_pitch + dy * 0.25))
            self.sync_guides_to_engine()
            return True
        if not self.active_handle: return False
        if self.active_handle == "sym_center":
            self.sym_state["cx"], self.sym_state["cy"] = float(pos.x()), float(pos.y())
            self.sync_symmetry_to_engine(); return True
        if self.active_handle == "sym_angle":
            deg = math.degrees(math.atan2(pos.y() - self.sym_state["cy"], pos.x() - self.sym_state["cx"]))
            inc = self.sym_state.get("snap_increment", 15)
            if shift_pressed or inc > 0: deg = round(deg / inc) * inc
            self.sym_state["angle"] = deg
            self.sync_symmetry_to_engine(); return True
        if self.active_handle == "guide_curv_center":
            self.guide_state["cx"], self.guide_state["cy"] = float(pos.x()), float(pos.y())
            self.sync_guides_to_engine(); return True
        if self.active_handle == "guide_curv_rotate":
            deg = math.degrees(math.atan2(pos.y() - self.guide_state["cy"], pos.x() - self.guide_state["cx"])) % 360.0
            if shift_pressed: deg = round(deg / 15.0) * 15.0
            self.guide_state["yaw"] = deg
            self.sync_guides_to_engine(); return True
        if self.active_handle.startswith("guide_"):
            n = self.active_handle.replace("guide_", "")
            if n in self.guide_state:
                self.guide_state[n] = QtCore.QPointF(pos.x(), pos.y())
                self.sync_guides_to_engine(); return True
        return False

    def mouse_release(self) -> None:
        self.active_handle = None
        self.curv_drag_rotate = False
        self.is_stroking = False
        self.snap_start_pt = None
        self.start_distance = (0.0, 0.0)
        self.locked_curve = None
        self.locked_dir = None
        self.current_stroke_pts = []

    def start_stroke_snap(self, start_pt: tuple[float, float]):
        self.is_stroking = True
        pt = QtCore.QPointF(start_pt[0], start_pt[1])
        self.snap_start_pt, self.locked_curve, self.locked_dir = pt, None, None
        self.hover_point = pt
        self.current_stroke_pts = [pt]
        gtype = self.guide_state["type"]

        if gtype == "straight":
            p0, p1 = self.guide_state["p0"], self.guide_state["p1"]
            dx, dy = p1.x() - p0.x(), p1.y() - p0.y()
            len2 = dx * dx + dy * dy
            if len2 > 1e-6:
                t = ((pt.x() - p0.x()) * dx + (pt.y() - p0.y()) * dy) / len2
                proj_x, proj_y = p0.x() + t * dx, p0.y() + t * dy
                self.start_distance = (pt.x() - proj_x, pt.y() - proj_y)
            else:
                self.start_distance = (0.0, 0.0)

        elif gtype == "curvilinear":
            self.dynamic_hover_curves = self._get_dynamic_curves_at_point(pt)
            mode = self.guide_state.get("snap_mode", "auto")
            if mode in ("v", "h", "d") and self.dynamic_hover_curves:
                matching = [c for c in self.dynamic_hover_curves if c.get("family") == mode or c.get("family", "").endswith(f"_{mode}")]
                if matching: self.locked_curve = matching[0]

    def snap_point(self, raw_x: float, raw_y: float, zoom: float = 1.0) -> tuple[float, float]:
        res = self._compute_snap(raw_x, raw_y, zoom)
        self.hover_point = QtCore.QPointF(res[0], res[1])
        if self.guide_state.get("type") == "curvilinear" and self.guide_state.get("show_hint", True):
            self.dynamic_hover_curves = self._get_dynamic_curves_at_point(self.hover_point)
        return res

    def _compute_snap(self, raw_x: float, raw_y: float, zoom: float = 1.0) -> tuple[float, float]:
        gtype = self.guide_state["type"]
        if gtype == "none" or not self.guide_state.get("snap_dynamic", True): return (raw_x, raw_y)
        pt = QtCore.QPointF(raw_x, raw_y)

        # 1. Straight Ruler: Infinite Painter parallel track projection
        if gtype == "straight":
            p0, p1 = self.guide_state["p0"], self.guide_state["p1"]
            dx, dy = p1.x() - p0.x(), p1.y() - p0.y()
            len2 = dx * dx + dy * dy
            if len2 > 1e-6:
                t = ((raw_x - p0.x()) * dx + (raw_y - p0.y()) * dy) / len2
                proj_x, proj_y = p0.x() + t * dx, p0.y() + t * dy
                if not self.is_stroking:
                    eff_r = self.guide_state.get("snap_radius", 32.0) / max(0.01, float(zoom))
                    d2 = (raw_x - proj_x)**2 + (raw_y - proj_y)**2
                    if d2 > eff_r * eff_r:
                        return (raw_x, raw_y)
                return (proj_x + self.start_distance[0], proj_y + self.start_distance[1])
            return (p0.x() + self.start_distance[0], p0.y() + self.start_distance[1])

        # 2. Cubic Bézier Curve
        if gtype == "curve_ruler":
            p0, p1, p2, p3 = self.guide_state["p0"], self.guide_state["p1"], self.guide_state["p2"], self.guide_state["p3"]
            best_t, best_d2 = 0.0, float("inf")
            for i in range(17):
                t, u = i / 16.0, 1.0 - (i / 16.0)
                bx = u**3 * p0.x() + 3 * u**2 * t * p1.x() + 3 * u * t**2 * p2.x() + t**3 * p3.x()
                by = u**3 * p0.y() + 3 * u**2 * t * p1.y() + 3 * u * t**2 * p2.y() + t**3 * p3.y()
                d2 = (bx - raw_x)**2 + (by - raw_y)**2
                if d2 < best_d2: best_d2, best_t = d2, t
            t = best_t
            for _ in range(4):
                u = 1.0 - t
                bx = u**3 * p0.x() + 3 * u**2 * t * p1.x() + 3 * u * t**2 * p2.x() + t**3 * p3.x()
                by = u**3 * p0.y() + 3 * u**2 * t * p1.y() + 3 * u * t**2 * p2.y() + t**3 * p3.y()
                dpx = 3 * (u**2 * (p1.x() - p0.x()) + 2 * u * t * (p2.x() - p1.x()) + t**2 * (p3.x() - p2.x()))
                dpy = 3 * (u**2 * (p1.y() - p0.y()) + 2 * u * t * (p2.y() - p1.y()) + t**2 * (p3.y() - p2.y()))
                fp = dpx * dpx + dpy * dpy
                if abs(fp) > 1e-6: t = max(0.0, min(1.0, t - ((bx - raw_x) * dpx + (by - raw_y) * dpy) / fp))
            u = 1.0 - t
            return (u**3 * p0.x() + 3 * u**2 * t * p1.x() + 3 * u * t**2 * p2.x() + t**3 * p3.x(),
                    u**3 * p0.y() + 3 * u**2 * t * p1.y() + 3 * u * t**2 * p2.y() + t**3 * p3.y())

        # 3. Perspectives (1P, 2P, 3P, Isometric): Infinite Painter origin ray track
        if gtype in ("one_point", "two_point", "three_point", "isometric"):
            start = self.snap_start_pt or pt
            if self.locked_dir is not None:
                t = (raw_x - start.x()) * self.locked_dir[0] + (raw_y - start.y()) * self.locked_dir[1]
                return (start.x() + t * self.locked_dir[0], start.y() + t * self.locked_dir[1])

            dx, dy = raw_x - start.x(), raw_y - start.y()
            dist = math.hypot(dx, dy)
            if dist < (2.5 / max(0.01, zoom)):
                return (start.x(), start.y())

            ux, uy = dx / dist, dy / dist
            candidates = []
            if gtype == "one_point":
                vpA = self.guide_state["vpA"]
                lA = math.hypot(vpA.x() - start.x(), vpA.y() - start.y()) or 1.0
                candidates.extend([((vpA.x() - start.x()) / lA, (vpA.y() - start.y()) / lA), (1.0, 0.0), (0.0, 1.0)])
            elif gtype == "two_point":
                vpA, vpB = self.guide_state["vpA"], self.guide_state["vpB"]
                lA = math.hypot(vpA.x() - start.x(), vpA.y() - start.y()) or 1.0
                lB = math.hypot(vpB.x() - start.x(), vpB.y() - start.y()) or 1.0
                candidates.extend([((vpA.x() - start.x()) / lA, (vpA.y() - start.y()) / lA), ((vpB.x() - start.x()) / lB, (vpB.y() - start.y()) / lB)])
                hdx, hdy = vpB.x() - vpA.x(), vpB.y() - vpA.y()
                hlen = math.hypot(hdx, hdy) or 1.0
                candidates.append((-hdy / hlen, hdx / hlen))
            elif gtype == "three_point":
                for n in ("vpA", "vpB", "vpC"):
                    l = math.hypot(self.guide_state[n].x() - start.x(), self.guide_state[n].y() - start.y()) or 1.0
                    candidates.append(((self.guide_state[n].x() - start.x()) / l, (self.guide_state[n].y() - start.y()) / l))
            elif gtype == "isometric":
                candidates = [(0.0, 1.0), (math.cos(math.pi / 6), math.sin(math.pi / 6)), (-math.cos(math.pi / 6), math.sin(math.pi / 6))]

            best_dir, max_dot = (1.0, 0.0), -1.0
            for c in candidates:
                dot = abs(c[0] * ux + c[1] * uy)
                if dot > max_dot: max_dot, best_dir = dot, c
            self.locked_dir = best_dir
            t = (raw_x - start.x()) * best_dir[0] + (raw_y - start.y()) * best_dir[1]
            return (start.x() + t * best_dir[0], start.y() + t * best_dir[1])

        # 4. Curvilinear 6P: Dynamic 3D curves through stylus contact point
        if gtype == "curvilinear":
            start = self.snap_start_pt or pt
            if self.locked_curve is not None:
                snapped_pt = self._closest_point_on_curve(self.locked_curve, pt)
                self.current_stroke_pts.append(snapped_pt)
                return (snapped_pt.x(), snapped_pt.y())

            dx, dy = raw_x - start.x(), raw_y - start.y()
            dist = math.hypot(dx, dy)

            curves = self.dynamic_hover_curves or self._get_dynamic_curves_at_point(start)
            mode = self.guide_state.get("snap_mode", "auto")
            if mode in ("v", "h", "d"):
                curves = [c for c in curves if c.get("family") == mode or c.get("family", "").endswith(f"_{mode}")]

            if not curves: return (raw_x, raw_y)

            # Explicit mode locks immediately on stroke
            if mode in ("v", "h", "d") and self.is_stroking:
                self.locked_curve = curves[0]
                snapped_pt = self._closest_point_on_curve(self.locked_curve, pt)
                return (snapped_pt.x(), snapped_pt.y())

            # Auto mode: wait until gesture moves at least lock_thresh pixels
            sens = self.guide_state.get("snap_sensitivity", 3.0)
            lock_thresh = max(2.5, (9.0 - sens * 1.5)) / max(0.01, zoom)

            if dist < lock_thresh:
                # Pre-lock phase: project onto closest curve without permanently locking
                best_curve, best_dist = None, float("inf")
                for c in curves:
                    cp = self._closest_point_on_curve(c, pt)
                    d = math.hypot(pt.x() - cp.x(), pt.y() - cp.y())
                    if d < best_dist:
                        best_dist, best_curve = d, c
                if best_curve is not None:
                    snapped_pt = self._closest_point_on_curve(best_curve, pt)
                    return (snapped_pt.x(), snapped_pt.y())
                return (raw_x, raw_y)

            # Gesture direction established: score by tangent alignment with motion vector
            ux, uy = dx / dist, dy / dist
            best_curve, best_score = None, -1.0
            for c in curves:
                cp = self._closest_point_on_curve(c, pt)
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
                if self.is_stroking:
                    self.locked_curve = best_curve
                snapped_pt = self._closest_point_on_curve(best_curve, pt)
                return (snapped_pt.x(), snapped_pt.y())
            return (raw_x, raw_y)


        return (raw_x, raw_y)



    def _get_dynamic_curves_at_point(self, click_pt: QtCore.QPointF) -> list:
        cx, cy = self.guide_state["cx"], self.guide_state["cy"]
        fov_rad = math.radians(self.guide_state["fov"])
        tan_f = math.tan(fov_rad / 4.0)
        base_r = self.guide_state.get("base_radius", 400.0)
        R = base_r / tan_f if tan_f > 1e-5 else 1e9

        X, Y = (click_pt.x() - cx) / R, -(click_pt.y() - cy) / R
        r2 = X * X + Y * Y
        denom = r2 + 1.0
        x3, y3, z3 = 2.0 * X / denom, 2.0 * Y / denom, (r2 - 1.0) / denom

        yaw_rad, pitch_rad = math.radians(self.guide_state["yaw"]), math.radians(self.guide_state["pitch"])
        xw, yw, zw = self._rotate_3d_forward(x3, y3, z3, yaw_rad, pitch_rad)

        def p3d_to_2d(gx, gy, gz):
            xc, yc, zc = self._rotate_3d_backward(gx, gy, gz, yaw_rad, pitch_rad)
            length = math.sqrt(xc * xc + yc * yc + zc * zc) or 1.0
            ux, uy, uz = xc / length, yc / length, zc / length
            if uz >= 0.999: return None
            return QtCore.QPointF(cx + (ux / (1.0 - uz)) * R, cy - (uy / (1.0 - uz)) * R)

        curves = []

        # 1. Vertical Curve (V) - Converges at Blue VP
        if self.guide_state.get("show_v", True) or self.guide_state.get("show_ground_verticals", False) or self.guide_state.get("show_ceiling_verticals", False) or self.guide_state.get("show_straight_verticals", False):
            a_v, b_v, c_v = self._rotate_3d_backward(zw, 0.0, -xw, yaw_rad, pitch_rad)
            if self.guide_state.get("show_straight_verticals", False):
                Tx, Ty, Tz = b_v * z3 - c_v * y3, c_v * x3 - a_v * z3, a_v * y3 - b_v * x3
                dz = 1.0 - z3
                dx, dy = (Tx * dz + x3 * Tz), -(Ty * dz + y3 * Tz)
                l = math.hypot(dx, dy) or 1.0
                dx, dy = dx / l, dy / l
                curves.append({"type": "line", "family": "ground_v",
                               "p1": QtCore.QPointF(click_pt.x() - dx * 20000.0, click_pt.y() - dy * 20000.0),
                               "p2": QtCore.QPointF(click_pt.x() + dx * 20000.0, click_pt.y() + dy * 20000.0),
                               "dir": QtCore.QPointF(dx, dy)})
            else:
                c_v = self._create_curve_from_normal(a_v, b_v, c_v, R, cx, cy, "ground_v")
                if c_v: curves.append(c_v)

        # 2. Transversal Curve (H / Ground X) - Converges at Red VP
        if self.guide_state.get("show_h", True) or self.guide_state.get("show_ground", False) or self.guide_state.get("show_ceiling", False):
            a_h, b_h, c_h = self._rotate_3d_backward(0.0, -zw, yw, yaw_rad, pitch_rad)
            c_h = self._create_curve_from_normal(a_h, b_h, c_h, R, cx, cy, "ground_x")
            if c_h: curves.append(c_h)

        # 3. Depth Curve (D / Ground Z) - Converges at Green VP
        if self.guide_state.get("show_d", True) or self.guide_state.get("show_ground", False) or self.guide_state.get("show_ceiling", False):
            a_d, b_d, c_d = self._rotate_3d_backward(-yw, xw, 0.0, yaw_rad, pitch_rad)
            c_d = self._create_curve_from_normal(a_d, b_d, c_d, R, cx, cy, "ground_z")
            if c_d: curves.append(c_d)

        return curves

    def _rotate_3d_forward(self, x, y, z, yaw_rad, pitch_rad):
        ch, sh, cv, sv = math.cos(yaw_rad), math.sin(yaw_rad), math.cos(pitch_rad), math.sin(pitch_rad)
        xr, yr, zr = x * ch - z * sh, y, x * sh + z * ch
        return xr, yr * cv - zr * sv, yr * sv + zr * cv

    def _rotate_3d_backward(self, x, y, z, yaw_rad, pitch_rad):
        ch, sh, cv, sv = math.cos(yaw_rad), math.sin(yaw_rad), math.cos(pitch_rad), math.sin(pitch_rad)
        xu, yu, zu = x, y * cv + z * sv, -y * sv + z * cv
        return xu * ch + zu * sh, yu, -xu * sh + zu * ch

    def _create_curve_from_normal(self, a, b, c, R, cx, cy, family):
        norm = math.sqrt(a * a + b * b + c * c)
        if norm > 1e-6: a, b, c = a / norm, b / norm, c / norm
        if abs(c) < 1e-4:
            denom = math.sqrt(a * a + b * b)
            if denom < 1e-4: return None
            dx, dy = -b / denom, -a / denom
            return {"type": "line", "family": family, "p1": QtCore.QPointF(cx + dx * 20000.0, cy + dy * 20000.0),
                    "p2": QtCore.QPointF(cx - dx * 20000.0, cy - dy * 20000.0), "dir": QtCore.QPointF(dx, dy)}
        cx_c, cy_c, radius = -R * a / c, R * b / c, R / abs(c)
        if radius > 20000.0:
            dist = math.hypot(cx_c, cy_c)
            if dist < 1e-4: return None
            nx, ny = cx_c / dist, cy_c / dist
            c_x, c_y = cx + (dist - radius) * nx, cy + (dist - radius) * ny
            return {"type": "line", "family": family, "p1": QtCore.QPointF(c_x - ny * 20000.0, c_y + nx * 20000.0),
                    "p2": QtCore.QPointF(c_x + ny * 20000.0, c_y - nx * 20000.0), "dir": QtCore.QPointF(-ny, nx)}
        return {"type": "circle", "family": family, "center": QtCore.QPointF(cx + cx_c, cy + cy_c), "radius": radius}

    def _closest_point_on_curve(self, curve, pt: QtCore.QPointF) -> QtCore.QPointF:
        if curve["type"] == "line":
            p1, p2 = curve["p1"], curve["p2"]
            v = p2 - p1
            len2 = v.x()**2 + v.y()**2
            if len2 < 1e-6: return p1
            t = ((pt.x() - p1.x()) * v.x() + (pt.y() - p1.y()) * v.y()) / len2
            return QtCore.QPointF(p1.x() + t * v.x(), p1.y() + t * v.y())
        if curve["type"] == "polyline":
            pts = curve.get("points", [])
            if not pts: return pt
            best_pt, best_d2 = pts[0], float("inf")
            for i in range(len(pts) - 1):
                p1, p2 = pts[i], pts[i + 1]
                vx, vy = p2.x() - p1.x(), p2.y() - p1.y()
                len2 = vx * vx + vy * vy
                t = 0.0 if len2 < 1e-6 else max(0.0, min(1.0, ((pt.x() - p1.x()) * vx + (pt.y() - p1.y()) * vy) / len2))
                cand = QtCore.QPointF(p1.x() + t * vx, p1.y() + t * vy)
                d2 = (cand.x() - pt.x())**2 + (cand.y() - pt.y())**2
                if d2 < best_d2: best_d2, best_pt = d2, cand
            return best_pt
        center, radius = curve["center"], curve["radius"]
        dx, dy = pt.x() - center.x(), pt.y() - center.y()
        dist = math.hypot(dx, dy)
        if dist > 1e-5: return QtCore.QPointF(center.x() + (dx / dist) * radius, center.y() + (dy / dist) * radius)
        return QtCore.QPointF(center.x() + radius, center.y())

    def sync_symmetry_to_engine(self):
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_symmetry_config"):
            mode_map = {"none": 0, "mirror": 1, "mirror_v": 1, "mirror_h": 1, "double_mirror": 2, "radial": 3, "kaleidoscope": 4}
            mode_id = mode_map.get(self.sym_state["mode"], 0)
            angle_rad = math.radians(self.sym_state["angle"])
            if self.sym_state["mode"] == "mirror_v": angle_rad = math.pi / 2.0
            elif self.sym_state["mode"] == "mirror_h": angle_rad = 0.0
            backend.set_symmetry_config(mode_id, self.sym_state["cx"], self.sym_state["cy"], angle_rad,
                                        self.sym_state.get("segments", 6), self.sym_state.get("stop_at_center", False))

    def sync_guides_to_engine(self):
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_guide_config"):
            gtype_map = {"none": 0, "straight": 1, "curve_ruler": 2, "curvilinear": 3, "one_point": 4, "two_point": 5, "three_point": 6, "isometric": 7}
            p0, p1 = self.guide_state.get("p0", QtCore.QPointF(0, 0)), self.guide_state.get("p1", QtCore.QPointF(100, 100))
            p2, p3 = self.guide_state.get("p2", QtCore.QPointF(200, 200)), self.guide_state.get("p3", QtCore.QPointF(300, 300))
            vpA, vpB = self.guide_state.get("vpA", QtCore.QPointF(400, 300)), self.guide_state.get("vpB", QtCore.QPointF(-1000, 300))
            vpC = self.guide_state.get("vpC", QtCore.QPointF(400, -2000))
            backend.set_guide_config(gtype_map.get(self.guide_state["type"], 0), p0.x(), p0.y(), p1.x(), p1.y(), p2.x(), p2.y(), p3.x(), p3.y(),
                                     vpA.x(), vpA.y(), vpB.x(), vpB.y(), vpC.x(), vpC.y(),
                                     self.guide_state.get("cx", 400.0), self.guide_state.get("cy", 300.0),
                                     self.guide_state.get("fov", 130.0), self.guide_state.get("pitch", 0.0),
                                     self.guide_state.get("yaw", 0.0), self.guide_state.get("snap_radius", 32.0))
