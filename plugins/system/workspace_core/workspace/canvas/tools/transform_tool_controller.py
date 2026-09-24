"""Free Transform 2D Interactive Tool Controller."""

import math
from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.engine.registry import EngineRegistry
from ui.core.tool_settings import default_tool_settings
from . import transform_distort as distort_geometry

class TransformToolController:
    """Controlador de Transformação Livre (Bounding Box, Escala, Rotação e Translação)."""

    def __init__(self, widget):
        self.widget = widget
        self.active: bool = False
        self.source_qimage: Optional[QtGui.QImage] = None
        self.source_rect: QtCore.QRectF = QtCore.QRectF()
        self.pivot: QtCore.QPointF = QtCore.QPointF()
        self.dx: float = 0.0
        self.dy: float = 0.0
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self.rotation: float = 0.0
        self.flip_h: bool = False
        self.flip_v: bool = False
        settings = default_tool_settings("transform")
        self.interp_mode = settings["interp_mode"]
        self.lock_aspect = settings["lock_aspect"]
        self.distort = settings["distort"]
        # Distorcer: cantos TL, TR, BR, BL na tela. None = caixa afim (livre).
        # Depois do primeiro arrasto distorcido a caixa fica neste modo até
        # aplicar ou cancelar.
        self.quad: Optional[list[QtCore.QPointF]] = None
        self.handle_dragged: Optional[str] = None
        self.mouse_press_pos: Optional[QtCore.QPointF] = None
        self.press_params: dict = {}

    def start_mode(self) -> bool:
        backend = EngineRegistry.instance().get_backend()
        if not backend or not hasattr(backend, "begin_transform"):
            return False

        if not backend.begin_transform():
            return False

        bx, by, bw, bh = backend.get_transform_source_bounds()
        px, py = backend.get_transform_pivot()
        qimg = backend.get_transform_source_qimage()

        self.source_rect = QtCore.QRectF(bx, by, bw, bh)
        self.pivot = QtCore.QPointF(px, py)
        self.source_qimage = qimg
        self.dx = 0.0
        self.dy = 0.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.rotation = 0.0
        self.flip_h = False
        self.flip_v = False
        self.quad = None
        self.active = True
        if hasattr(self.widget, "strokeStarted"):
            self.widget.strokeStarted.emit()
        self.widget.update()
        return True

    def commit(self):
        if not self.active:
            return
        backend = EngineRegistry.instance().get_backend()
        if backend and self.quad is not None:
            backend.commit_transform_distort(distort_geometry.flatten(self.quad), interp_mode=self.interp_mode)
        elif backend and hasattr(backend, "commit_transform"):
            backend.commit_transform(
                dx=self.dx,
                dy=self.dy,
                scale_x=self.scale_x,
                scale_y=self.scale_y,
                rotation_deg=self.rotation,
                pivot_x=self.pivot.x(),
                pivot_y=self.pivot.y(),
                flip_h=self.flip_h,
                flip_v=self.flip_v,
                interp_mode=self.interp_mode
            )
        self.active = False
        self.source_qimage = None
        self.quad = None
        self.widget.update()
        if hasattr(self.widget, "strokeFinished"):
            self.widget.strokeFinished.emit()

    def cancel(self):
        if not self.active:
            return
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "cancel_transform"):
            backend.cancel_transform()
        self.active = False
        self.source_qimage = None
        self.quad = None
        self.widget.update()
        if hasattr(self.widget, "strokeFinished"):
            self.widget.strokeFinished.emit()


    def flip_horizontal(self):
        if self.active:
            if self.quad is not None:
                self.quad = distort_geometry.mirror(self.quad, horizontal=True)
            else:
                self.flip_h = not self.flip_h
            self.widget.update()

    def flip_vertical(self):
        if self.active:
            if self.quad is not None:
                self.quad = distort_geometry.mirror(self.quad, horizontal=False)
            else:
                self.flip_v = not self.flip_v
            self.widget.update()

    def rotate_90(self, clockwise: bool = True):
        if self.active:
            if self.quad is not None:
                self.quad = distort_geometry.rotate_90(self.quad, clockwise=clockwise)
            else:
                delta = 90.0 if clockwise else -90.0
                self.rotation = (self.rotation + delta) % 360.0
            self.widget.update()

    def begin_drag(self, handle: str, canvas_pt: QtCore.QPointF) -> None:
        """Guarda o estado no clique; apply_drag calcula tudo relativo a ele."""
        self.handle_dragged = handle
        self.mouse_press_pos = canvas_pt
        self.press_params = {
            "dx": self.dx,
            "dy": self.dy,
            "sx": self.scale_x,
            "sy": self.scale_y,
            "rot": self.rotation,
            "pivot": QtCore.QPointF(self.pivot),
            "quad": ([QtCore.QPointF(p) for p in self.quad] if self.quad is not None
                     else distort_geometry.quad_from_matrix(self.source_rect, self.get_transform_matrix())),
        }

    def get_transform_matrix(self) -> QtGui.QTransform:
        if self.quad is not None:
            matrix = distort_geometry.matrix_from_quad(self.source_rect, self.quad)
            if matrix is not None:
                return matrix
        t = QtGui.QTransform()
        pv = self.pivot
        t.translate(pv.x() + self.dx, pv.y() + self.dy)
        t.rotate(self.rotation)
        sx = -self.scale_x if self.flip_h else self.scale_x
        sy = -self.scale_y if self.flip_v else self.scale_y
        t.scale(sx, sy)
        t.translate(-pv.x(), -pv.y())
        return t

    def hit_test_handle(self, canvas_pt: QtCore.QPointF, zoom: float) -> Optional[str]:
        if not self.active:
            return None

        t_mat: QtGui.QTransform = self.get_transform_matrix()
        src_rect = self.source_rect
        pv = self.pivot
        zoom_factor = max(0.01, zoom)
        hit_dist = 12.0 / zoom_factor

        pv_mapped = t_mat.map(pv)
        if self.quad is None and (canvas_pt - pv_mapped).manhattanLength() <= hit_dist:
            return "pivot"

        handles = {
            "tl": t_mat.map(src_rect.topLeft()),
            "tr": t_mat.map(src_rect.topRight()),
            "br": t_mat.map(src_rect.bottomRight()),
            "bl": t_mat.map(src_rect.bottomLeft()),
            "tc": t_mat.map(QtCore.QPointF(src_rect.center().x(), src_rect.top())),
            "bc": t_mat.map(QtCore.QPointF(src_rect.center().x(), src_rect.bottom())),
            "ml": t_mat.map(QtCore.QPointF(src_rect.left(), src_rect.center().y())),
            "mr": t_mat.map(QtCore.QPointF(src_rect.right(), src_rect.center().y())),
        }

        for h_name, h_pos in handles.items():
            if (canvas_pt - h_pos).manhattanLength() <= hit_dist:
                return h_name

        rot_dist = 30.0 / zoom_factor
        for h_name in (() if self.quad is not None else ("tl", "tr", "br", "bl")):
            if (canvas_pt - handles[h_name]).manhattanLength() <= rot_dist:
                return "rotate"

        poly = QtGui.QPolygonF([handles["tl"], handles["tr"], handles["br"], handles["bl"]])
        if poly.containsPoint(canvas_pt, QtCore.Qt.OddEvenFill):
            return "move"

        return None

    def apply_drag(self, canvas_pt: QtCore.QPointF, modifiers: QtCore.Qt.KeyboardModifiers):
        if not self.active or not self.handle_dragged or not self.mouse_press_pos:
            return

        handle = self.handle_dragged
        start_pt = self.mouse_press_pos
        init_p = self.press_params
        is_shift = bool(modifiers & QtCore.Qt.ShiftModifier)

        if self.quad is not None or (self.distort and handle in distort_geometry.CORNERS + tuple(distort_geometry.EDGES)):
            moved = distort_geometry.drag(init_p["quad"], handle, canvas_pt - start_pt)
            if distort_geometry.is_convex_quad(moved):  # nunca deixa o quad dobrar sobre si
                self.quad = moved
            return

        if handle == "move":
            self.dx = init_p["dx"] + (canvas_pt.x() - start_pt.x())
            self.dy = init_p["dy"] + (canvas_pt.y() - start_pt.y())

        elif handle == "pivot":
            self.pivot = canvas_pt

        elif handle == "rotate":
            pv = self.pivot
            pv_map = QtCore.QPointF(pv.x() + self.dx, pv.y() + self.dy)
            ang1 = math.atan2(start_pt.y() - pv_map.y(), start_pt.x() - pv_map.x())
            ang2 = math.atan2(canvas_pt.y() - pv_map.y(), canvas_pt.x() - pv_map.x())
            d_deg = math.degrees(ang2 - ang1)
            raw_rot = init_p["rot"] + d_deg
            if is_shift:
                self.rotation = round(raw_rot / 15.0) * 15.0
            else:
                self.rotation = raw_rot

        elif handle in ("tl", "tr", "bl", "br", "tc", "bc", "ml", "mr"):
            src_rect = self.source_rect
            if src_rect.width() <= 0 or src_rect.height() <= 0:
                return

            pv = self.pivot
            pv_map = QtCore.QPointF(pv.x() + self.dx, pv.y() + self.dy)
            
            rad = math.radians(self.rotation)
            cosR = math.cos(-rad)
            sinR = math.sin(-rad)

            d_cur = canvas_pt - pv_map
            d_start = start_pt - pv_map

            cur_lx = d_cur.x() * cosR - d_cur.y() * sinR
            cur_ly = d_cur.x() * sinR + d_cur.y() * cosR

            start_lx = d_start.x() * cosR - d_start.y() * sinR
            start_ly = d_start.x() * sinR + d_start.y() * cosR

            factor_x = 1.0 if abs(start_lx) < 1e-4 else (cur_lx / start_lx)
            factor_y = 1.0 if abs(start_ly) < 1e-4 else (cur_ly / start_ly)

            if handle in ("tl", "tr", "bl", "br"):
                if is_shift or self.lock_aspect:
                    avg = (abs(factor_x) + abs(factor_y)) / 2.0
                    factor_x = avg * (1.0 if factor_x >= 0 else -1.0)
                    factor_y = avg * (1.0 if factor_y >= 0 else -1.0)
                self.scale_x = max(0.01, abs(init_p["sx"] * factor_x))
                self.scale_y = max(0.01, abs(init_p["sy"] * factor_y))
            elif handle in ("ml", "mr"):
                self.scale_x = max(0.01, abs(init_p["sx"] * factor_x))
            elif handle in ("tc", "bc"):
                self.scale_y = max(0.01, abs(init_p["sy"] * factor_y))
