"""CanvasInputRouter — Routes mouse, tablet, touch and keyboard events to active tool controllers."""

import time
import math
from typing import Optional, TYPE_CHECKING
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.engine.backend import PointerEvent

if TYPE_CHECKING:
    from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget

class CanvasInputRouter:
    """Roteador modular de eventos de ponteiro e teclado para o RenderWidget."""

    def __init__(self, widget):
        self.widget = widget
        self._previous_engine_type: Optional[int] = None

    def handle_pointer_press(self, pos: QtCore.QPointF, button: QtCore.Qt.MouseButton, pressure: float, modifiers: QtCore.Qt.KeyboardModifiers, is_eraser_tip: bool = False, timestamp: float = 0.0):
        w: "RenderWidget" = self.widget
        effective_tool = "eraser" if is_eraser_tip else w.active_tool

        if hasattr(w, "geometry_ctrl"):
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            pt = QtCore.QPointF(world_evt.x, world_evt.y)
            is_right = (button == QtCore.Qt.RightButton)
            if w.geometry_ctrl.mouse_press(pt, w.zoom, is_right):
                w.update()
                return

        if button == QtCore.Qt.LeftButton and (effective_tool == "eyedrop" or (modifiers & QtCore.Qt.AltModifier)):
            w.eyedrop_ctrl.active = True
            w.eyedrop_ctrl.pos = pos
            w.eyedrop_ctrl.old_color = w.eyedrop_ctrl.current_color
            w.eyedrop_ctrl.do_sample(pos.x(), pos.y())
            w.update()
            return

        if button == QtCore.Qt.LeftButton and effective_tool == "text":
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            if w._active_text_editor:
                if not w._active_text_editor.geometry().contains(QtCore.QPoint(int(pos.x()), int(pos.y()))):
                    w.commit_text_overlay()
                    w.open_text_editor(world_evt.x, world_evt.y)
            else:
                w.open_text_editor(world_evt.x, world_evt.y)
            return

        if button == QtCore.Qt.LeftButton and effective_tool == "bucket":
            w.do_flood_fill(pos.x(), pos.y())
            return

        if button == QtCore.Qt.LeftButton and effective_tool == "wand":
            w.selection_ctrl.do_magic_wand_select(pos.x(), pos.y())
            return

        if button == QtCore.Qt.LeftButton and effective_tool in ("rect_select", "ellipse_select"):
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            w.selection_ctrl.drag_active = True
            w.selection_ctrl.drag_start = QtCore.QPointF(world_evt.x, world_evt.y)
            w.selection_ctrl.drag_current = w.selection_ctrl.drag_start
            w.update()
            return

        if button == QtCore.Qt.LeftButton and (effective_tool == "shapes" or effective_tool.startswith("shape_")):
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            w.shape_ctrl.drag_active = True
            w.shape_ctrl.drag_start = QtCore.QPointF(world_evt.x, world_evt.y)
            w.shape_ctrl.drag_current = w.shape_ctrl.drag_start
            w.update()
            return

        if effective_tool == "lasso":
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            pt = QtCore.QPointF(world_evt.x, world_evt.y)
            ltype = w.selection_ctrl.lasso_settings.get("lasso_type", "freehand")
            if ltype == "freehand" and button == QtCore.Qt.LeftButton:
                w.selection_ctrl.lasso_is_drawing = True
                w.selection_ctrl.lasso_points = [pt]
                w.update()
                return
            elif ltype == "polygonal":
                if button == QtCore.Qt.LeftButton:
                    if w.selection_ctrl.lasso_points and (pt - w.selection_ctrl.lasso_points[0]).manhattanLength() < max(6.0, 12.0 / max(0.01, w.zoom)) and len(w.selection_ctrl.lasso_points) >= 3:
                        w.selection_ctrl.finish_lasso_selection()
                    else:
                        w.selection_ctrl.lasso_points.append(pt)
                    w.update()
                    return
                elif button == QtCore.Qt.RightButton:
                    w.selection_ctrl.lasso_points.clear()
                    w.selection_ctrl.lasso_hover_pt = None
                    w.update()
                    return

        if effective_tool == "transform" or w.transform_ctrl.active:
            if button == QtCore.Qt.LeftButton:
                world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
                pt = QtCore.QPointF(world_evt.x, world_evt.y)
                if w.transform_ctrl.active:
                    handle = w.transform_ctrl.hit_test_handle(pt, w.zoom)
                    if handle:
                        w.transform_ctrl.handle_dragged = handle
                        w.transform_ctrl.mouse_press_pos = pt
                        w.transform_ctrl.press_params = {
                            "dx": w.transform_ctrl.dx,
                            "dy": w.transform_ctrl.dy,
                            "sx": w.transform_ctrl.scale_x,
                            "sy": w.transform_ctrl.scale_y,
                            "rot": w.transform_ctrl.rotation,
                            "pivot": QtCore.QPointF(w.transform_ctrl.pivot)
                        }
                        w.update()
                        return
                else:
                    w.start_transform_mode()
                    return

        if (button == QtCore.Qt.RightButton and (modifiers & QtCore.Qt.AltModifier)) or (button == QtCore.Qt.LeftButton and (modifiers & QtCore.Qt.ControlModifier) and (modifiers & QtCore.Qt.AltModifier)):
            w.is_zoom_dragging = True
            w.zoom_drag_start_pos = pos
            return

        if button == QtCore.Qt.MiddleButton or (button == QtCore.Qt.LeftButton and (modifiers & QtCore.Qt.ShiftModifier)):
            w.is_panning = True
            w.last_mouse_pos = pos
            return

        if button == QtCore.Qt.LeftButton:
            if is_eraser_tip and w.backend and hasattr(w.backend, "set_engine_type") and hasattr(w.backend, "get_active_engine_type"):
                self._previous_engine_type = w.backend.get_active_engine_type()
                w.backend.set_engine_type(6)  # aladyn::engine::brush::EngineType::Eraser
            w.start_stroke(pos.x(), pos.y(), max(0.02, pressure), timestamp)

    def handle_pointer_move(self, pos: QtCore.QPointF, pressure: float, modifiers: QtCore.Qt.KeyboardModifiers, is_eraser_tip: bool = False, timestamp: float = 0.0):
        w: "RenderWidget" = self.widget
        if w.drawing:
            w.paint_stroke(pos.x(), pos.y(), max(0.02, pressure), timestamp)
            if hasattr(w, "geometry_ctrl") and hasattr(w, "_last_draw_pos"):
                w.geometry_ctrl.hover_point = QtCore.QPointF(w._last_draw_pos[0], w._last_draw_pos[1])
            return

        if hasattr(w, "geometry_ctrl") and (w.geometry_ctrl.active_handle or w.geometry_ctrl.curv_drag_rotate):
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            pt = QtCore.QPointF(world_evt.x, world_evt.y)
            shift_pressed = bool(modifiers & QtCore.Qt.ShiftModifier)
            if w.geometry_ctrl.mouse_move(pt, shift_pressed):
                w.update()
                return

        if w.transform_ctrl.active:
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            pt = QtCore.QPointF(world_evt.x, world_evt.y)
            if w.transform_ctrl.handle_dragged:
                w.transform_ctrl.apply_drag(pt, modifiers)
                w.update()
                return
            else:
                handle = w.transform_ctrl.hit_test_handle(pt, w.zoom)
                self.update_transform_cursor(handle)

        if w.eyedrop_ctrl.active:
            w.eyedrop_ctrl.pos = pos
            w.eyedrop_ctrl.do_sample(pos.x(), pos.y())
            w.update()
            return

        if w.selection_ctrl.drag_active:
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            w.selection_ctrl.drag_current = QtCore.QPointF(world_evt.x, world_evt.y)
            w.update()
            return

        if w.shape_ctrl.drag_active:
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            w.shape_ctrl.drag_current = QtCore.QPointF(world_evt.x, world_evt.y)
            w.update()
            return

        if w.active_tool == "lasso":
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            pt = QtCore.QPointF(world_evt.x, world_evt.y)
            if w.selection_ctrl.lasso_is_drawing:
                if not w.selection_ctrl.lasso_points or (pt - w.selection_ctrl.lasso_points[-1]).manhattanLength() >= 2.0:
                    w.selection_ctrl.lasso_points.append(pt)
                    w.update()
                return
            elif w.selection_ctrl.lasso_settings.get("lasso_type") == "polygonal" and w.selection_ctrl.lasso_points:
                w.selection_ctrl.lasso_hover_pt = pt
                w.update()
                return

        if w.is_zoom_dragging:
            delta_x = pos.x() - w.zoom_drag_start_pos.x()
            delta_y = w.zoom_drag_start_pos.y() - pos.y()
            delta = delta_x if abs(delta_x) > abs(delta_y) else delta_y
            factor = 1.0 + (delta * 0.02)
            w._apply_anchored_zoom(factor, w.zoom_drag_start_pos)
            w.zoom_drag_start_pos = pos
            return

        if w.is_panning:
            delta = pos - w.last_mouse_pos
            w.pan_x += delta.x()
            w.pan_y += delta.y()
            w.last_mouse_pos = pos
            rot_rad = math.radians(w.rotation)
            w.bridge_client.update_view(w.zoom, w.pan_x, w.pan_y, rot_rad)
            w.cameraChanged.emit(w.zoom, w.pan_x, w.pan_y, w.rotation, float(w.width()), float(w.height()))
            if w._active_text_editor:
                w._active_text_editor.update_screen_position()
            w.update()
            return

        if hasattr(w, "geometry_ctrl") and (w.geometry_ctrl.guide_state.get("type") != "none" or w.geometry_ctrl.sym_state.get("mode") != "none"):
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            w.geometry_ctrl.handle_hover(QtCore.QPointF(world_evt.x, world_evt.y))
            w.update()

    def handle_pointer_release(self, pos: QtCore.QPointF, button: QtCore.Qt.MouseButton, modifiers: QtCore.Qt.KeyboardModifiers):
        w: "RenderWidget" = self.widget
        if hasattr(w, "geometry_ctrl") and (w.geometry_ctrl.active_handle or w.geometry_ctrl.curv_drag_rotate):
            w.geometry_ctrl.mouse_release()
            w.update()
            return

        if w.is_zoom_dragging:
            w.is_zoom_dragging = False
            return
        if w.transform_ctrl.active and w.transform_ctrl.handle_dragged and button == QtCore.Qt.LeftButton:
            w.transform_ctrl.handle_dragged = None
            w.transform_ctrl.mouse_press_pos = None
            w.unsetCursor()
            w.update()
            return

        if w.eyedrop_ctrl.active and button == QtCore.Qt.LeftButton:
            w.eyedrop_ctrl.active = False
            w.update()
            return

        if w.selection_ctrl.drag_active and button == QtCore.Qt.LeftButton:
            w.selection_ctrl.drag_active = False
            w.selection_ctrl.finish_geom_selection()
            return

        if w.shape_ctrl.drag_active and button == QtCore.Qt.LeftButton:
            w.shape_ctrl.drag_active = False
            w.shape_ctrl.commit_to_layer()
            return

        if w.active_tool == "lasso" and w.selection_ctrl.lasso_is_drawing and button == QtCore.Qt.LeftButton:
            w.selection_ctrl.lasso_is_drawing = False
            w.selection_ctrl.finish_lasso_selection()
            return

        if button == QtCore.Qt.LeftButton and w.drawing:
            w.end_stroke(pos.x(), pos.y())
            if self._previous_engine_type is not None:
                if w.backend and hasattr(w.backend, "set_engine_type"):
                    w.backend.set_engine_type(self._previous_engine_type)
                self._previous_engine_type = None
        elif button in (QtCore.Qt.MiddleButton, QtCore.Qt.LeftButton):
            w.is_panning = False

    def update_transform_cursor(self, handle_name: Optional[str]):
        w: "RenderWidget" = self.widget
        if handle_name == "move":
            w.setCursor(QtCore.Qt.SizeAllCursor)
        elif handle_name == "pivot":
            w.setCursor(QtCore.Qt.CrossCursor)
        elif handle_name == "rotate":
            w.setCursor(QtCore.Qt.PointingHandCursor)
        elif handle_name in ("tl", "br"):
            w.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif handle_name in ("tr", "bl"):
            w.setCursor(QtCore.Qt.SizeBDiagCursor)
        elif handle_name in ("tc", "bc"):
            w.setCursor(QtCore.Qt.SizeVerCursor)
        elif handle_name in ("ml", "mr"):
            w.setCursor(QtCore.Qt.SizeHorCursor)
        else:
            w.unsetCursor()

    def handle_key_press(self, event: QtGui.QKeyEvent) -> bool:
        w: "RenderWidget" = self.widget
        modifiers = event.modifiers()
        from ui.core.engine.registry import EngineRegistry
        from ui.core.shortcut_bindings import ShortcutBindings
        backend = EngineRegistry.instance().get_backend()

        if w.transform_ctrl.active:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                w.commit_transform()
                return True
            elif event.key() == QtCore.Qt.Key_Escape:
                w.cancel_transform()
                return True
            elif event.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right, QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
                step = 10.0 if (modifiers & QtCore.Qt.ShiftModifier) else 1.0
                if event.key() == QtCore.Qt.Key_Left:
                    w.transform_ctrl.dx -= step
                elif event.key() == QtCore.Qt.Key_Right:
                    w.transform_ctrl.dx += step
                elif event.key() == QtCore.Qt.Key_Up:
                    w.transform_ctrl.dy -= step
                elif event.key() == QtCore.Qt.Key_Down:
                    w.transform_ctrl.dy += step
                w.update()
                return True

        if ShortcutBindings.matches("tool_transform", event):
            w.start_transform_mode()
            return True
        if ShortcutBindings.matches("select_deselect", event):
            if backend and hasattr(backend, "clear_selection"):
                backend.clear_selection()
                w.selection_ctrl.selection_timer.stop()
                w.update()
                return True
        if ShortcutBindings.matches("select_invert", event):
            if backend and hasattr(backend, "invert_selection"):
                backend.invert_selection()
                if backend.has_selection():
                    w.selection_ctrl.selection_timer.start()
                w.update()
                return True
        if ShortcutBindings.matches("select_all", event):
            if backend and hasattr(backend, "select_all"):
                backend.select_all()
                w.selection_ctrl.selection_timer.start()
                w.update()
                return True

        if event.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            if backend and hasattr(backend, "has_selection") and backend.has_selection():
                if hasattr(backend, "delete_selection_on_active_layer"):
                    ok = backend.delete_selection_on_active_layer()
                    if ok:
                        w.update()
                        w.strokeFinished.emit()
                        return True
        return False
