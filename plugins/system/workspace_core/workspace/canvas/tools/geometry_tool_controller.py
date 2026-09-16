"""Tool Controller for Symmetry, Guides, and Snapping Interactions.

Coordinates mouse, touch, and stylus events, interactive handle hit-testing,
and backend engine synchronization.
Delegates analytical math and point projections to GeometrySnappingEngine and Camera3DProjector.
Strictly decoupled in compliance with ARCcC v2 (< 250 LOC).
"""

import math
import copy
import os
from PySide6 import QtCore
from ui.core.engine.registry import EngineRegistry
from ..math.camera_3d_projector import (
    rotate_3d_forward,
    rotate_3d_backward,
    create_curve_from_normal,
    closest_point_on_curve
)
from .geometry_snapping_engine import GeometrySnappingEngine


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

        # Fase C3.2 -- toggle temporario de comparacao nativo vs Python
        # (default off; usado so para validacao manual de "feel" antes de
        # flipar o padrao em producao -- ver Fase C3.3/C3.4). Estado nativo
        # de perspectiva reaproveita locked_dir (mesmo shape); curvilinear
        # nativo usa indice em vez de dict, por isso tem estado proprio.
        self._snap_use_native_perspective = os.environ.get("LUMENIA_SNAP_NATIVE_PERSPECTIVE", "0") == "1"
        self._snap_use_native_curvilinear = os.environ.get("LUMENIA_SNAP_NATIVE_CURVILINEAR", "0") == "1"
        self._native_curv_locked_index = -1
        self._native_stroke_candidates_flat = []

        # Fase C3.5 (refinamento) -- referencia de direcao para RE-travar
        # apos um break-away. Usar sempre o ponto de pressao original
        # (snap_start_pt) deixa essa corda cada vez mais desatualizada num
        # traco longo e rapido (pior com mouse, cujos eventos sao mais
        # espacados/saltados que com stylus) -- e essa desatualizacao, nao a
        # trava rigida em si, que fazia o re-lock continuar errando mesmo
        # depois do fix de break-away. `anchor` acompanha o ultimo ponto
        # travado com sucesso e vira a referencia para reavaliacoes; None
        # ate a primeira trava, quando cai de volta no ponto de pressao
        # (preserva o comportamento de trava inicial ja validado na C3.3).
        self._native_curv_anchor = None
        self._native_persp_anchor = None

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
        doc_w, doc_h = max(1.0, float(doc_w)), max(1.0, float(doc_h))
        cx, cy, base_r = doc_w / 2.0, doc_h / 2.0, min(doc_w, doc_h) * 0.42
        if not getattr(self, "_custom_sym_center", False):
            self.sym_state["cx"], self.sym_state["cy"] = cx, cy
        self.guide_state.update({
            "cx": cx, "cy": cy, "base_radius": base_r,
            "p0": QtCore.QPointF(cx - doc_w * 0.35, cy), "p1": QtCore.QPointF(cx + doc_w * 0.35, cy),
            "p2": QtCore.QPointF(cx - doc_w * 0.15, cy - doc_h * 0.18), "p3": QtCore.QPointF(cx + doc_w * 0.15, cy - doc_h * 0.18),
            "vpA": QtCore.QPointF(cx - doc_w * 0.55, cy), "vpB": QtCore.QPointF(cx + doc_w * 0.55, cy),
            "vpC": QtCore.QPointF(cx, cy - doc_h * 0.65)
        })
        self.sync_symmetry_to_engine()
        self.sync_guides_to_engine()

    def load_document_state(self, document):
        # Reset defaults first so omitted fields never leak from another tab.
        defaults = type(self)(self.widget)
        self.guide_state = defaults.guide_state
        self.sym_state = defaults.sym_state
        self._custom_sym_center = False
        self._loading_document = True
        try:
            self.center_on_document(document.width, document.height)
            self.guide_state.update(copy.deepcopy(document.guide_state))
            self.sym_state.update(copy.deepcopy(document.sym_state))
            self.sync_guides_to_engine()
            self.sync_symmetry_to_engine()
        finally:
            self._loading_document = False

    def _store_document_state(self, key, state):
        if getattr(self, "_loading_document", False):
            return
        from ui.core.document.manager import DocumentManager
        document = DocumentManager.instance().active_document()
        if document is not None and getattr(document, key) != state:
            setattr(document, key, copy.deepcopy(state))
            document.mark_dirty(key)

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
            self.guide_state["yaw"] = (sy - dx * 0.25) % 360.0
            self.guide_state["pitch"] = max(-90.0, min(90.0, sp + dy * 0.25))
            self.sync_guides_to_engine()
            return True
        if not self.active_handle:
            return False
        if self.active_handle == "sym_center":
            self.sym_state["cx"], self.sym_state["cy"] = float(pos.x()), float(pos.y())
            self.sync_symmetry_to_engine()
            return True
        if self.active_handle == "sym_angle":
            deg = math.degrees(math.atan2(pos.y() - self.sym_state["cy"], pos.x() - self.sym_state["cx"]))
            inc = self.sym_state.get("snap_increment", 15)
            if shift_pressed and inc > 0:
                deg = round(deg / inc) * inc
            self.sym_state["angle"] = deg % 360.0
            self.sync_symmetry_to_engine()
            return True
        if self.active_handle == "guide_curv_center":
            self.guide_state["cx"], self.guide_state["cy"] = float(pos.x()), float(pos.y())
            self.sync_guides_to_engine()
            return True
        if self.active_handle == "guide_curv_rotate":
            deg = math.degrees(math.atan2(pos.y() - self.guide_state["cy"], pos.x() - self.guide_state["cx"])) % 360.0
            if shift_pressed:
                deg = round(deg / 15.0) * 15.0
            self.guide_state["yaw"] = deg
            self.sync_guides_to_engine()
            return True
        if self.active_handle.startswith("guide_"):
            n = self.active_handle.replace("guide_", "")
            if n in self.guide_state:
                self.guide_state[n] = QtCore.QPointF(pos.x(), pos.y())
                self.sync_guides_to_engine()
                return True
        return False

    def mouse_release(self) -> None:
        self.active_handle, self.curv_drag_rotate, self.is_stroking = None, False, False
        self.snap_start_pt, self.start_distance, self.locked_curve = None, (0.0, 0.0), None
        self.locked_dir, self.stroke_candidate_curves, self.current_stroke_pts = None, [], []
        self._native_curv_locked_index, self._native_stroke_candidates_flat = -1, []
        self._native_curv_anchor, self._native_persp_anchor = None, None

    def start_stroke_snap(self, start_pt: tuple[float, float]):
        self.is_stroking = True
        pt = QtCore.QPointF(start_pt[0], start_pt[1])
        self.snap_start_pt, self.locked_curve, self.locked_dir = pt, None, None
        self.hover_point, self.current_stroke_pts = pt, [pt]
        self._native_curv_locked_index, self._native_stroke_candidates_flat = -1, []
        self._native_curv_anchor, self._native_persp_anchor = None, None
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
            if self._snap_use_native_perspective:
                native_res = self._compute_snap_perspective_native(raw_x, raw_y, zoom)
                if native_res is not None:
                    return native_res
            pt_res, locked = GeometrySnappingEngine.snap_ray_perspective(
                raw_x, raw_y, zoom, self.guide_state, self.snap_start_pt, self.locked_dir
            )
            if locked is not None:
                self.locked_dir = locked
            return pt_res

        if gtype == "curvilinear":
            if self._snap_use_native_curvilinear:
                native_res = self._compute_snap_curvilinear_native(raw_x, raw_y, zoom)
                if native_res is not None:
                    return native_res
            curves = self.stroke_candidate_curves if (self.is_stroking and self.stroke_candidate_curves) else (
                self.dynamic_hover_curves or GeometrySnappingEngine.get_dynamic_curves_at_point(self.guide_state, self.snap_start_pt or QtCore.QPointF(raw_x, raw_y))
            )
            pt_res, locked = GeometrySnappingEngine.snap_curvilinear(
                raw_x, raw_y, zoom, self.guide_state, self.snap_start_pt, self.locked_curve, curves, self.is_stroking
            )
            if locked is not None:
                self.locked_curve = locked
                self.current_stroke_pts.append(QtCore.QPointF(pt_res[0], pt_res[1]))
            return pt_res

        return (raw_x, raw_y)

    # Fase C3.2 -- caminhos nativos opcionais (toggle de comparacao). Ambos
    # retornam None (fallback silencioso para Python) se o backend ativo nao
    # suportar o metodo -- nunca quebram a UI se o nativo nao estiver
    # disponivel (ex.: testes sem extensao compilada).

    def _compute_snap_perspective_native(self, raw_x: float, raw_y: float, zoom: float):
        b = EngineRegistry.instance().get_backend()
        if not b or not hasattr(b, "snap_perspective"):
            return None
        # Fase C3.5 (refinamento) -- ver comentario no __init__. Enquanto a
        # trava se mantem, o anchor permanece sobre a mesma reta (e' a
        # projecao do frame anterior), entao usa-lo aqui nao muda o ponto
        # projetado; o que muda e' so a reavaliacao apos um break-away, que
        # passa a usar uma referencia recente em vez do ponto de pressao.
        anchor = self._native_persp_anchor or self.snap_start_pt or QtCore.QPointF(raw_x, raw_y)
        has_lock = self.locked_dir is not None
        ldx, ldy = self.locked_dir if has_lock else (0.0, 0.0)
        x, y, has_lock_out, ndx, ndy = b.snap_perspective(
            raw_x, raw_y, anchor.x(), anchor.y(), has_lock, ldx, ldy, zoom
        )
        if has_lock_out:
            self.locked_dir = (ndx, ndy)
            self._native_persp_anchor = QtCore.QPointF(x, y)
        return (x, y)

    def _compute_snap_curvilinear_native(self, raw_x: float, raw_y: float, zoom: float):
        b = EngineRegistry.instance().get_backend()
        if not b or not hasattr(b, "snap_curvilinear") or not hasattr(b, "get_curvilinear_candidates"):
            return None
        press_start = self.snap_start_pt or QtCore.QPointF(raw_x, raw_y)
        candidates = self._native_stroke_candidates_flat if (self.is_stroking and self._native_stroke_candidates_flat) else (
            b.get_curvilinear_candidates(press_start.x(), press_start.y())
        )
        # Fase C3.5 (refinamento) -- ver comentario no __init__. A geracao de
        # candidatas continua ancorada na pressao (define o conjunto de
        # curvas do traco inteiro); so a referencia passada para pontuar
        # direcao/re-travar usa o anchor recente.
        anchor = self._native_curv_anchor or press_start
        x, y, new_idx = b.snap_curvilinear(
            raw_x, raw_y, anchor.x(), anchor.y(), candidates, self._native_curv_locked_index, self.is_stroking, zoom
        )
        if new_idx >= 0:
            self._native_curv_locked_index = new_idx
            self._native_stroke_candidates_flat = candidates
            self._native_curv_anchor = QtCore.QPointF(x, y)
        return (x, y)

    # Delegation aliases for backward compatibility and sub-systems
    def _get_dynamic_curves_at_point(self, click_pt: QtCore.QPointF) -> list:
        return GeometrySnappingEngine.get_dynamic_curves_at_point(self.guide_state, click_pt)

    def _find_nearest_primary_grid_curve(self, pt: QtCore.QPointF, max_dist: float = 24.0):
        return GeometrySnappingEngine.find_nearest_primary_grid_curve(self.guide_state, pt, max_dist)

    def _closest_point_on_curve(self, curve, pt: QtCore.QPointF) -> QtCore.QPointF:
        return closest_point_on_curve(curve, pt)

    def _rotate_3d_forward(self, x, y, z, yaw_rad, pitch_rad):
        return rotate_3d_forward(x, y, z, yaw_rad, pitch_rad)

    def _rotate_3d_backward(self, x, y, z, yaw_rad, pitch_rad):
        return rotate_3d_backward(x, y, z, yaw_rad, pitch_rad)

    def _create_curve_from_normal(self, a, b, c, R, cx, cy, family):
        return create_curve_from_normal(a, b, c, R, cx, cy, family)

    def sync_symmetry_to_engine(self):
        self._store_document_state("sym_state", self.sym_state)
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "set_symmetry_config"):
            m_map = {"none": 0, "mirror": 1, "mirror_v": 1, "mirror_h": 1, "double_mirror": 2, "radial": 3, "kaleidoscope": 4}
            rad = math.pi / 2.0 if self.sym_state["mode"] == "mirror_v" else (0.0 if self.sym_state["mode"] == "mirror_h" else math.radians(self.sym_state["angle"]))
            b.set_symmetry_config(
                m_map.get(self.sym_state["mode"], 0), self.sym_state["cx"], self.sym_state["cy"], rad,
                self.sym_state.get("segments", 6), self.sym_state.get("stop_at_center", False)
            )

    def sync_guides_to_engine(self):
        self._store_document_state("guide_state", self.guide_state)
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "set_guide_config"):
            gmap = {"none": 0, "straight": 1, "curve_ruler": 2, "curvilinear": 3, "one_point": 4, "two_point": 5, "three_point": 6, "isometric": 7}
            p0, p1 = self.guide_state.get("p0", QtCore.QPointF(0, 0)), self.guide_state.get("p1", QtCore.QPointF(100, 100))
            p2, p3 = self.guide_state.get("p2", QtCore.QPointF(200, 200)), self.guide_state.get("p3", QtCore.QPointF(300, 300))
            vpA, vpB, vpC = self.guide_state.get("vpA", QtCore.QPointF(400, 300)), self.guide_state.get("vpB", QtCore.QPointF(-1000, 300)), self.guide_state.get("vpC", QtCore.QPointF(400, -2000))
            b.set_guide_config(
                gmap.get(self.guide_state["type"], 0), p0.x(), p0.y(), p1.x(), p1.y(), p2.x(), p2.y(), p3.x(), p3.y(),
                vpA.x(), vpA.y(), vpB.x(), vpB.y(), vpC.x(), vpC.y(),
                self.guide_state.get("cx", 400.0), self.guide_state.get("cy", 300.0),
                self.guide_state.get("fov", 130.0), self.guide_state.get("pitch", 0.0),
                self.guide_state.get("yaw", 0.0), self.guide_state.get("snap_radius", 32.0)
            )
        if b and hasattr(b, "set_curvilinear_guide_config"):
            # Completa os campos de GuideConfig usados só pelo Curvilinear
            # (Fase C2b) — canal de dados adicional; a UI ainda calcula o
            # snap em Python (GeometrySnappingEngine), isto só deixa o motor
            # C++ pronto para ser chamado quando a delegação for ativada.
            smap = {"auto": 0, "v": 1, "h": 2, "d": 3}
            b.set_curvilinear_guide_config(
                self.guide_state.get("base_radius", 400.0), self.guide_state.get("density", 30.0),
                self.guide_state.get("show_v", True), self.guide_state.get("show_h", True), self.guide_state.get("show_d", True),
                self.guide_state.get("show_ground", False), self.guide_state.get("show_ceiling", False),
                self.guide_state.get("show_ground_verticals", False), self.guide_state.get("show_ceiling_verticals", False),
                self.guide_state.get("show_straight_verticals", False),
                smap.get(self.guide_state.get("snap_mode", "auto"), 0), self.guide_state.get("snap_sensitivity", 3.0)
            )
