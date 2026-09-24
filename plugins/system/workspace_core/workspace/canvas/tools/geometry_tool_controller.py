"""Tool Controller for Symmetry, Guides, and Snapping Interactions.

Coordinates mouse, touch, and stylus events, interactive handle hit-testing,
and backend engine synchronization.
Delegates analytical math and point projections to GeometrySnappingEngine and Camera3DProjector.

Colaboradores (2026-09-24, o arquivo estava na parede dos 450 linhas):
- `NativeGeometrySnap` (geometry_native_snap.py): snap pelo motor C++, com
  o próprio estado de trava e âncoras;
- `geometry_engine_sync.push_guides/push_symmetry`: escritor único no motor;
- o documento ativo guarda guias e simetria por `Document.store_*_state`.
"""

import copy
import math
from PySide6 import QtCore
from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry
from ..math.camera_3d_projector import closest_point_on_curve
from .geometry_engine_sync import push_guides, push_symmetry
from .geometry_native_snap import NativeGeometrySnap, first_not_none
from .geometry_snapping_engine import GeometrySnappingEngine
from ui.core.geometry.synced_dict import SyncedDict


class GeometryToolController:
    """Unified UI controller for symmetry, rulers, and 6P curvilinear perspective."""

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
        self.stroke_candidate_curves = []
        self.current_stroke_pts = []

        # Snap pelo motor C++ (toggle de comparação da Fase C3.2).
        self.native_snap = NativeGeometrySnap(lambda: EngineRegistry.instance().get_backend())
        # Durante load_document_state o documento não é reescrito com o que
        # ele mesmo acabou de entregar.
        self._loading_document = False

        self.sym_state = SyncedDict({
            "mode": "none", "cx": 400.0, "cy": 300.0, "angle": 90.0,
            "segments": 6, "stop_at_center": False, "locked": False,
            "hidden": False, "snap_increment": 15
        }, on_change=self.sync_symmetry_to_engine)

        self.guide_state = SyncedDict({
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
        }, on_change=self.sync_guides_to_engine)

    def center_on_document(self, doc_w: float, doc_h: float):
        doc_w, doc_h = max(1.0, float(doc_w)), max(1.0, float(doc_h))
        cx, cy, base_r = doc_w / 2.0, doc_h / 2.0, min(doc_w, doc_h) * 0.42
        self.sym_state.update({"cx": cx, "cy": cy}, sync=False)
        self.guide_state.update({
            "cx": cx, "cy": cy, "base_radius": base_r,
            "p0": QtCore.QPointF(cx - doc_w * 0.35, cy), "p1": QtCore.QPointF(cx + doc_w * 0.35, cy),
            "p2": QtCore.QPointF(cx - doc_w * 0.15, cy - doc_h * 0.18), "p3": QtCore.QPointF(cx + doc_w * 0.15, cy - doc_h * 0.18),
            "vpA": QtCore.QPointF(cx - doc_w * 0.55, cy), "vpB": QtCore.QPointF(cx + doc_w * 0.55, cy),
            "vpC": QtCore.QPointF(cx, cy - doc_h * 0.65)
        }, sync=False)
        self.sync_symmetry_to_engine()
        self.sync_guides_to_engine()

    def load_document_state(self, document):
        # Reset defaults first so omitted fields never leak from another tab.
        # `reset()` preserva a identidade do SyncedDict (e o on_change ja
        # vinculado a `self`) -- reatribuir o atributo trocaria pelo
        # SyncedDict de `defaults`, vinculado ao controller errado.
        defaults = type(self)(self.widget)
        self.guide_state.reset(dict(defaults.guide_state), sync=False)
        self.sym_state.reset(dict(defaults.sym_state), sync=False)
        self._loading_document = True
        try:
            self.center_on_document(document.width, document.height)
            self.guide_state.update(copy.deepcopy(document.guide_state), sync=False)
            self.sym_state.update(copy.deepcopy(document.sym_state), sync=False)
            self.sync_guides_to_engine()
            self.sync_symmetry_to_engine()
        finally:
            self._loading_document = False

    def _active_document(self):
        """Documento que guarda guias e simetria (nenhum durante o load dele mesmo)."""
        return None if self._loading_document else DocumentManager.instance().active_document()

    def handle_hover(self, doc_pt: QtCore.QPointF):
        self.hover_point = doc_pt
        if self.guide_state["type"] == "curvilinear" and self.guide_state.get("show_hint", True):
            self.dynamic_hover_curves = GeometrySnappingEngine.get_dynamic_curves_at_point(self.guide_state, doc_pt)
        elif not self.is_stroking:
            self.dynamic_hover_curves = []

    def hit_test(self, pos: QtCore.QPointF, zoom: float) -> str | None:
        tol = 16.0 / max(0.01, zoom)
        if self.sym_state["mode"] != "none" and not self.sym_state["locked"] and not self.sym_state["hidden"]:
            cx, cy = self.sym_state["cx"], self.sym_state["cy"]
            if math.hypot(pos.x() - cx, pos.y() - cy) <= tol:
                return "sym_center"
            rad, dist = math.radians(self.sym_state["angle"]), 80.0 / max(0.01, zoom)
            if math.hypot(pos.x() - (cx + dist * math.cos(rad)), pos.y() - (cy + dist * math.sin(rad))) <= tol:
                return "sym_angle"

        gtype = self.guide_state["type"]
        if gtype == "straight":
            for n in ("p0", "p1"):
                if math.hypot(pos.x() - self.guide_state[n].x(), pos.y() - self.guide_state[n].y()) <= tol:
                    return f"guide_{n}"
        elif gtype == "curve_ruler":
            for n in ("p0", "p1", "p2", "p3"):
                if math.hypot(pos.x() - self.guide_state[n].x(), pos.y() - self.guide_state[n].y()) <= tol:
                    return f"guide_{n}"
        elif gtype in ("one_point", "two_point", "three_point"):
            for n in ("vpA", "vpB", "vpC"):
                if n in self.guide_state and math.hypot(pos.x() - self.guide_state[n].x(), pos.y() - self.guide_state[n].y()) <= tol:
                    return f"guide_{n}"
        elif gtype == "curvilinear":
            cx, cy = self.guide_state["cx"], self.guide_state["cy"]
            if math.hypot(pos.x() - cx, pos.y() - cy) <= tol:
                return "guide_curv_center"
            yaw_rad = math.radians(self.guide_state["yaw"])
            hx, hy = cx + (80.0 / max(0.01, zoom)) * math.cos(yaw_rad), cy + (80.0 / max(0.01, zoom)) * math.sin(yaw_rad)
            if math.hypot(pos.x() - hx, pos.y() - hy) <= tol:
                return "guide_curv_rotate"
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
            sy, sp = self.curv_start_angles
            self.guide_state.update({
                "yaw": (sy - dx * 0.25) % 360.0,
                "pitch": max(-90.0, min(90.0, sp + dy * 0.25)),
            })
            return True
        if not self.active_handle:
            return False
        if self.active_handle == "sym_center":
            self.sym_state.update({"cx": float(pos.x()), "cy": float(pos.y())})
            return True
        if self.active_handle == "sym_angle":
            deg = math.degrees(math.atan2(pos.y() - self.sym_state["cy"], pos.x() - self.sym_state["cx"]))
            inc = self.sym_state.get("snap_increment", 15)
            if shift_pressed and inc > 0:
                deg = round(deg / inc) * inc
            self.sym_state["angle"] = deg % 360.0
            return True
        if self.active_handle == "guide_curv_center":
            self.guide_state.update({"cx": float(pos.x()), "cy": float(pos.y())})
            return True
        if self.active_handle == "guide_curv_rotate":
            deg = math.degrees(math.atan2(pos.y() - self.guide_state["cy"], pos.x() - self.guide_state["cx"])) % 360.0
            if shift_pressed:
                deg = round(deg / 15.0) * 15.0
            self.guide_state["yaw"] = deg
            return True
        if self.active_handle.startswith("guide_"):
            n = self.active_handle.replace("guide_", "")
            if n in self.guide_state:
                self.guide_state[n] = QtCore.QPointF(pos.x(), pos.y())
                return True
        return False

    def mouse_release(self) -> None:
        self.active_handle, self.curv_drag_rotate, self.is_stroking = None, False, False
        self.snap_start_pt, self.start_distance, self.locked_curve = None, (0.0, 0.0), None
        self.locked_dir, self.stroke_candidate_curves, self.current_stroke_pts = None, [], []
        self.native_snap.reset()

    def start_stroke_snap(self, start_pt: tuple[float, float]):
        self.is_stroking = True
        pt = QtCore.QPointF(start_pt[0], start_pt[1])
        self.snap_start_pt, self.locked_curve, self.locked_dir = pt, None, None
        self.hover_point, self.current_stroke_pts = pt, [pt]
        self.native_snap.reset()
        gtype = self.guide_state["type"]

        if gtype == "straight":
            p0, p1 = self.guide_state["p0"], self.guide_state["p1"]
            dx, dy = p1.x() - p0.x(), p1.y() - p0.y()
            len2 = dx * dx + dy * dy
            if len2 > 1e-6:
                t = ((pt.x() - p0.x()) * dx + (pt.y() - p0.y()) * dy) / len2
                self.start_distance = (pt.x() - (p0.x() + t * dx), pt.y() - (p0.y() + t * dy))
            else:
                self.start_distance = (0.0, 0.0)

        elif gtype == "curvilinear":
            near_grid = GeometrySnappingEngine.find_nearest_primary_grid_curve(self.guide_state, pt, 24.0)
            if near_grid is not None:
                pt = closest_point_on_curve(near_grid, pt)
                self.snap_start_pt = pt
            self.stroke_candidate_curves = GeometrySnappingEngine.get_dynamic_curves_at_point(self.guide_state, pt)
            if near_grid is not None:
                self.stroke_candidate_curves.insert(0, near_grid)
            self.dynamic_hover_curves = list(self.stroke_candidate_curves)
            mode = self.guide_state.get("snap_mode", "auto")
            if mode in ("v", "h", "d") and self.stroke_candidate_curves:
                matching = [c for c in self.stroke_candidate_curves if c.get("family") == mode or c.get("family", "").endswith(f"_{mode}")]
                if matching:
                    self.locked_curve = matching[0]

    def snap_point(self, raw_x: float, raw_y: float, zoom: float = 1.0) -> tuple[float, float]:
        res = self._compute_snap(raw_x, raw_y, zoom)
        self.hover_point = QtCore.QPointF(res[0], res[1])
        if self.guide_state.get("type") == "curvilinear" and self.guide_state.get("show_hint", True):
            self.dynamic_hover_curves = GeometrySnappingEngine.get_dynamic_curves_at_point(self.guide_state, self.hover_point)
        return res

    def _compute_snap(self, raw_x: float, raw_y: float, zoom: float = 1.0) -> tuple[float, float]:
        gtype = self.guide_state["type"]
        if gtype == "none" or not self.guide_state.get("snap_dynamic", True):
            return (raw_x, raw_y)

        if gtype == "straight":
            return GeometrySnappingEngine.snap_straight(raw_x, raw_y, zoom, self.guide_state, self.is_stroking, self.start_distance)

        if gtype == "curve_ruler":
            return GeometrySnappingEngine.snap_bezier(raw_x, raw_y, self.guide_state)

        if gtype in ("one_point", "two_point", "three_point", "isometric"):
            if self.native_snap.use_perspective:
                native = self.native_snap.perspective(raw_x, raw_y, zoom, self.snap_start_pt, self.locked_dir)
                if native is not None:
                    point, locked = native
                    if locked is not None:
                        self.locked_dir = locked
                    return point
            pt_res, locked = GeometrySnappingEngine.snap_ray_perspective(
                raw_x, raw_y, zoom, self.guide_state, self.snap_start_pt, self.locked_dir
            )
            if locked is not None:
                self.locked_dir = locked
            return pt_res

        if gtype == "curvilinear":
            if self.native_snap.use_curvilinear:
                native = self.native_snap.curvilinear(raw_x, raw_y, zoom, self.snap_start_pt, self.is_stroking)
                if native is not None:
                    return native
            curves = self.stroke_candidate_curves if (self.is_stroking and self.stroke_candidate_curves) else (
                self.dynamic_hover_curves or GeometrySnappingEngine.get_dynamic_curves_at_point(self.guide_state, first_not_none(self.snap_start_pt, QtCore.QPointF(raw_x, raw_y)))
            )
            pt_res, locked = GeometrySnappingEngine.snap_curvilinear(
                raw_x, raw_y, zoom, self.guide_state, self.snap_start_pt, self.locked_curve, curves, self.is_stroking
            )
            if locked is not None:
                self.locked_curve = locked
                self.current_stroke_pts.append(QtCore.QPointF(pt_res[0], pt_res[1]))
            return pt_res

        return (raw_x, raw_y)

    def sync_symmetry_to_engine(self):
        document = self._active_document()
        if document is not None:
            document.store_sym_state(self.sym_state)
        push_symmetry(EngineRegistry.instance().get_backend(), self.sym_state)

    def sync_guides_to_engine(self):
        document = self._active_document()
        if document is not None:
            document.store_guide_state(self.guide_state)
        push_guides(EngineRegistry.instance().get_backend(), self.guide_state)
