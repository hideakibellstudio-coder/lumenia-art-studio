"""CanvasCompatMixin — Compatibility property proxies for legacy tests and external caller access."""

from PySide6 import QtCore, QtGui
from typing import Optional

class CanvasCompatMixin:
    """Fornece propriedades de compatibilidade para controladores do canvas."""

    @property
    def renderer(self):
        return self.bridge_client

    @property
    def input_adapter(self):
        return self.bridge_client.input_adapter

    # ── Camera Proxies ──
    @property
    def zoom(self) -> float: return self.camera.zoom
    @zoom.setter
    def zoom(self, v: float): self.camera.zoom = v

    @property
    def pan_x(self) -> float: return self.camera.pan_x
    @pan_x.setter
    def pan_x(self, v: float): self.camera.pan_x = v

    @property
    def pan_y(self) -> float: return self.camera.pan_y
    @pan_y.setter
    def pan_y(self, v: float): self.camera.pan_y = v

    @property
    def rotation(self) -> float: return self.camera.rotation
    @rotation.setter
    def rotation(self, v: float): self.camera.rotation = v

    @property
    def flip_x(self) -> bool:
        return getattr(self.camera, "flip_horizontal", False)
    @flip_x.setter
    def flip_x(self, v: bool) -> None:
        if hasattr(self, "camera"):
            new_v = bool(v)
            if getattr(self.camera, "flip_horizontal", False) != new_v:
                self.camera.flip_horizontal = new_v
                if hasattr(self, "cameraChanged"):
                    self.cameraChanged.emit(
                        getattr(self, "zoom", 1.0),
                        getattr(self, "pan_x", 0.0),
                        getattr(self, "pan_y", 0.0),
                        getattr(self, "rotation", 0.0),
                        float(self.width() if hasattr(self, "width") else 800),
                        float(self.height() if hasattr(self, "height") else 600)
                    )

    @property
    def flip_y(self) -> bool:
        return getattr(self.camera, "flip_vertical", False)
    @flip_y.setter
    def flip_y(self, v: bool) -> None:
        if hasattr(self, "camera"):
            new_v = bool(v)
            if getattr(self.camera, "flip_vertical", False) != new_v:
                self.camera.flip_vertical = new_v
                if hasattr(self, "cameraChanged"):
                    self.cameraChanged.emit(
                        getattr(self, "zoom", 1.0),
                        getattr(self, "pan_x", 0.0),
                        getattr(self, "pan_y", 0.0),
                        getattr(self, "rotation", 0.0),
                        float(self.width() if hasattr(self, "width") else 800),
                        float(self.height() if hasattr(self, "height") else 600)
                    )

    # ── Tool Controller Proxies ──
    @property
    def geometry_controller(self):
        return getattr(self, "geometry_ctrl", None)

    @property
    def _eyedropper_active(self) -> bool: return self.eyedrop_ctrl.active
    @_eyedropper_active.setter
    def _eyedropper_active(self, v: bool): self.eyedrop_ctrl.active = v

    @property
    def _eyedropper_pos(self) -> QtCore.QPointF: return self.eyedrop_ctrl.pos
    @_eyedropper_pos.setter
    def _eyedropper_pos(self, v: QtCore.QPointF): self.eyedrop_ctrl.pos = v

    @property
    def _eyedrop_settings(self) -> dict: return self.eyedrop_ctrl.settings
    @property
    def _wand_settings(self) -> dict: return self.selection_ctrl.wand_settings
    @property
    def _geom_select_settings(self) -> dict: return self.selection_ctrl.geom_select_settings
    @property
    def _lasso_settings(self) -> dict: return self.selection_ctrl.lasso_settings

    @property
    def _sel_drag_active(self) -> bool: return self.selection_ctrl.drag_active
    @_sel_drag_active.setter
    def _sel_drag_active(self, v: bool): self.selection_ctrl.drag_active = v

    @property
    def _sel_drag_start(self) -> QtCore.QPointF: return self.selection_ctrl.drag_start
    @_sel_drag_start.setter
    def _sel_drag_start(self, v: QtCore.QPointF): self.selection_ctrl.drag_start = v

    @property
    def _sel_drag_current(self) -> QtCore.QPointF: return self.selection_ctrl.drag_current
    @_sel_drag_current.setter
    def _sel_drag_current(self, v: QtCore.QPointF): self.selection_ctrl.drag_current = v

    @property
    def _lasso_points(self) -> list: return self.selection_ctrl.lasso_points
    @_lasso_points.setter
    def _lasso_points(self, v: list): self.selection_ctrl.lasso_points = v

    @property
    def _lasso_is_drawing(self) -> bool: return self.selection_ctrl.lasso_is_drawing
    @_lasso_is_drawing.setter
    def _lasso_is_drawing(self, v: bool): self.selection_ctrl.lasso_is_drawing = v

    @property
    def _shape_settings(self) -> dict: return self.shape_ctrl.settings
    @property
    def _shape_drag_active(self) -> bool: return self.shape_ctrl.drag_active
    @_shape_drag_active.setter
    def _shape_drag_active(self, v: bool): self.shape_ctrl.drag_active = v

    @property
    def _transform_active(self) -> bool: return self.transform_ctrl.active
    @_transform_active.setter
    def _transform_active(self, v: bool): self.transform_ctrl.active = v

    @property
    def active_color(self) -> QtGui.QColor:
        return getattr(self, "_active_draw_color", QtGui.QColor(0, 0, 0, 255))
    @active_color.setter
    def active_color(self, v: QtGui.QColor):
        self._active_draw_color = v
