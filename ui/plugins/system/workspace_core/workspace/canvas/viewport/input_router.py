"""CanvasInputRouter — leva mouse, caneta e toque às ferramentas do canvas.

O teclado é do `CanvasKeyRouter` (`key_router.py`), separado em 2026-09-25.
"""

from typing import Any, Optional, Protocol, runtime_checkable
from PySide6 import QtCore

from ui.core.engine.engine_type import EngineType


@runtime_checkable
class RouterCanvas(Protocol):
    """O que o roteador do ponteiro usa do canvas (34 membros; o teclado está em
    `key_router.py`, com contrato próprio).

    Até 2026-09-25 este arquivo importava o `RenderWidget` da pasta mãe só
    para anotar tipo (o ciclo canvas ↔ viewport). Membro novo usado aqui entra
    neste contrato; `tests/test_canvas_contracts.py` confere que o
    `RenderWidget` o cumpre.
    """
    active_tool: str
    drawing: bool
    is_panning: bool
    is_space_held: bool
    is_zoom_dragging: bool
    last_mouse_pos: QtCore.QPointF
    zoom_drag_start_pos: QtCore.QPointF
    pan_x: float
    pan_y: float
    zoom: float
    active_text_editor: Any
    backend: Any
    stroke: Any
    cursor_ctrl: Any
    eyedrop_ctrl: Any
    geometry_ctrl: Any
    selection_ctrl: Any
    shape_ctrl: Any
    transform_ctrl: Any
    strokeStarted: Any
    strokeFinished: Any

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> Any: ...
    def start_stroke(self, screen_x: float, screen_y: float, pressure: float, timestamp: float = 0.0,
                     tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0) -> Any: ...
    def paint_stroke(self, screen_x: float, screen_y: float, pressure: float, timestamp: float = 0.0,
                     tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0) -> Any: ...
    def end_stroke(self, screen_x: Optional[float] = None, screen_y: Optional[float] = None) -> Any: ...
    def publish_view(self, zoom_changed: bool = False, notify_camera: bool = True) -> None: ...
    def apply_anchored_zoom(self, factor: float, cursor_pos: QtCore.QPointF) -> Any: ...
    def start_transform_mode(self) -> bool: ...
    def do_flood_fill(self, screen_x: float, screen_y: float) -> Any: ...
    def open_text_editor(self, canvas_x: float, canvas_y: float) -> Any: ...
    def commit_text_overlay(self) -> Any: ...
    def setCursor(self, cursor: Any) -> None: ...
    def unsetCursor(self) -> None: ...
    def update(self) -> None: ...


class CanvasInputRouter:
    """Roteador dos eventos de ponteiro (apertar, arrastar, soltar) do canvas."""

    def __init__(self, widget: RouterCanvas):
        self.widget = widget
        self._previous_engine_type: Optional[int] = None

    def handle_pointer_press(self, pos: QtCore.QPointF, button: QtCore.Qt.MouseButton, pressure: float, modifiers: QtCore.Qt.KeyboardModifiers, is_eraser_tip: bool = False, timestamp: float = 0.0, tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0):
        """Apertar: a primeira regra que consome o clique vence, nesta ordem.

        Navegação (meio ou espaço) → alças das guias → conta-gotas (ou Alt) →
        ferramenta de clique (texto, balde, varinha, seleção, forma) → laço →
        transformação → zoom por arraste → traço. Dividido em passos em
        2026-09-25 (complexidade 26); `tests/test_canvas_input_router.py`
        confere cada ramo.
        """
        w: RouterCanvas = self.widget
        tool = "eraser" if is_eraser_tip else w.active_tool
        left = button == QtCore.Qt.LeftButton
        if button == QtCore.Qt.MiddleButton or (left and w.is_space_held):
            self._start_pan(pos)
            return
        world = self._world(pos)
        if w.geometry_ctrl.mouse_press(world, w.zoom, button == QtCore.Qt.RightButton):
            w.update()
            return
        if left and (tool == "eyedrop" or (modifiers & QtCore.Qt.AltModifier)):
            self._start_eyedrop(pos)
            return
        if left and self._press_click_tool(tool, pos, world):
            return
        if tool == "lasso" and self._press_lasso(button, world):
            return
        if (tool == "transform" or w.transform_ctrl.active) and left and self._press_transform(world):
            return
        if (button == QtCore.Qt.RightButton and (modifiers & QtCore.Qt.AltModifier)) or (left and (modifiers & QtCore.Qt.ControlModifier) and (modifiers & QtCore.Qt.AltModifier)):
            w.is_zoom_dragging = True
            w.zoom_drag_start_pos = pos
            w.setCursor(QtCore.Qt.SizeVerCursor)
            return
        if left:
            self._press_stroke(pos, pressure, modifiers, is_eraser_tip, timestamp, tilt_x, tilt_y, twist)

    def _world(self, pos: QtCore.QPointF) -> QtCore.QPointF:
        world_evt = self.widget.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
        return QtCore.QPointF(world_evt.x, world_evt.y)

    def _start_pan(self, pos: QtCore.QPointF) -> None:
        w = self.widget
        w.is_panning = True
        w.last_mouse_pos = pos
        w.setCursor(QtCore.Qt.ClosedHandCursor)
        w.update()

    def _start_eyedrop(self, pos: QtCore.QPointF) -> None:
        w = self.widget
        w.eyedrop_ctrl.active = True
        w.eyedrop_ctrl.pos = pos
        w.eyedrop_ctrl.old_color = w.eyedrop_ctrl.current_color
        w.eyedrop_ctrl.do_sample(pos.x(), pos.y())
        w.update()

    def _press_click_tool(self, tool: str, pos: QtCore.QPointF, world: QtCore.QPointF) -> bool:
        """Ferramentas que agem no clique esquerdo. Devolve se consumiu o clique."""
        w = self.widget
        if tool == "text":
            editor = w.active_text_editor
            if editor is None:
                w.open_text_editor(world.x(), world.y())
            elif not editor.geometry().contains(QtCore.QPoint(int(pos.x()), int(pos.y()))):
                w.commit_text_overlay()
                w.open_text_editor(world.x(), world.y())
            return True
        if tool == "bucket":
            w.do_flood_fill(pos.x(), pos.y())
            return True
        if tool == "wand":
            w.selection_ctrl.do_magic_wand_select(pos.x(), pos.y())
            return True
        if tool in ("rect_select", "ellipse_select"):
            self._start_drag(w.selection_ctrl, world)
            w.update()
            return True
        if tool == "shapes" or tool.startswith("shape_"):
            self._start_drag(w.shape_ctrl, world)
            w.strokeStarted.emit()
            w.update()
            return True
        return False

    @staticmethod
    def _start_drag(ctrl: Any, world: QtCore.QPointF) -> None:
        ctrl.drag_active = True
        ctrl.drag_start = world
        ctrl.drag_current = world

    def _press_lasso(self, button: QtCore.Qt.MouseButton, pt: QtCore.QPointF) -> bool:
        w = self.widget
        sel = w.selection_ctrl
        ltype = sel.lasso_settings.get("lasso_type", "freehand")
        if ltype == "freehand" and button == QtCore.Qt.LeftButton:
            sel.lasso_is_drawing = True
            sel.lasso_points = [pt]
        elif ltype == "polygonal" and button == QtCore.Qt.LeftButton:
            close_radius = max(6.0, 12.0 / max(0.01, w.zoom))
            if len(sel.lasso_points) >= 3 and (pt - sel.lasso_points[0]).manhattanLength() < close_radius:
                sel.finish_lasso_selection()
            else:
                sel.lasso_points.append(pt)
        elif ltype == "polygonal" and button == QtCore.Qt.RightButton:
            sel.lasso_points.clear()
            sel.lasso_hover_pt = None
        else:
            return False
        w.update()
        return True

    def _press_transform(self, pt: QtCore.QPointF) -> bool:
        w = self.widget
        if not w.transform_ctrl.active:
            w.start_transform_mode()
            return True
        handle = w.transform_ctrl.hit_test_handle(pt, w.zoom)
        if handle:
            w.transform_ctrl.begin_drag(handle, pt)
            w.update()
            return True
        return False

    def _press_stroke(self, pos, pressure, modifiers, is_eraser_tip, timestamp, tilt_x, tilt_y, twist) -> None:
        w = self.widget
        if is_eraser_tip and w.backend:
            self._previous_engine_type = w.backend.get_active_engine_type()
            w.backend.set_engine_type(EngineType.ERASER)
        p0 = w.stroke.last_end_screen
        if (modifiers & QtCore.Qt.ShiftModifier) and p0 is not None:
            # Linha reta desde o fim do último traço.
            w.start_stroke(p0.x(), p0.y(), max(0.02, pressure), timestamp, tilt_x, tilt_y, twist)
            steps = 10
            for s in range(1, steps + 1):
                t = s / steps
                ix = p0.x() + (pos.x() - p0.x()) * t
                iy = p0.y() + (pos.y() - p0.y()) * t
                w.paint_stroke(ix, iy, max(0.02, pressure), timestamp, tilt_x, tilt_y, twist)
        else:
            w.start_stroke(pos.x(), pos.y(), max(0.02, pressure), timestamp, tilt_x, tilt_y, twist)

    def handle_pointer_move(self, pos: QtCore.QPointF, pressure: float, modifiers: QtCore.Qt.KeyboardModifiers, is_eraser_tip: bool = False, timestamp: float = 0.0, tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0):
        w: RouterCanvas = self.widget
        if w.is_panning:
            delta = pos - w.last_mouse_pos
            w.pan_x += delta.x()
            w.pan_y += delta.y()
            w.last_mouse_pos = pos
            w.publish_view()
            return

        if w.drawing:
            w.paint_stroke(pos.x(), pos.y(), max(0.02, pressure), timestamp, tilt_x, tilt_y, twist)
            last = w.stroke.last_draw_pos
            if last is not None:
                w.geometry_ctrl.hover_point = QtCore.QPointF(last[0], last[1])
            return

        if w.geometry_ctrl.active_handle or w.geometry_ctrl.curv_drag_rotate:
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
            w.apply_anchored_zoom(factor, w.zoom_drag_start_pos)
            w.zoom_drag_start_pos = pos
            return

        if w.geometry_ctrl.guide_state.get("type") != "none" or w.geometry_ctrl.sym_state.get("mode") != "none":
            world_evt = w.to_canvas(pos.x(), pos.y(), 1.0, 0.0)
            w.geometry_ctrl.handle_hover(QtCore.QPointF(world_evt.x, world_evt.y))
            w.update()

    def handle_pointer_release(self, pos: QtCore.QPointF, button: QtCore.Qt.MouseButton, modifiers: QtCore.Qt.KeyboardModifiers):
        w: RouterCanvas = self.widget

        # ── Liberação de Panning / Navegação ──
        if w.is_panning and button in (QtCore.Qt.MiddleButton, QtCore.Qt.LeftButton):
            w.is_panning = False
            if w.is_space_held:
                w.setCursor(QtCore.Qt.OpenHandCursor)
            else:
                w.cursor_ctrl.restore_tool_cursor()
            w.update()
            return

        if w.geometry_ctrl.active_handle or w.geometry_ctrl.curv_drag_rotate:
            w.geometry_ctrl.mouse_release()
            w.update()
            return

        if w.is_zoom_dragging:
            w.is_zoom_dragging = False
            w.cursor_ctrl.restore_tool_cursor()
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
                if w.backend:
                    w.backend.set_engine_type(self._previous_engine_type)
                self._previous_engine_type = None

    def update_transform_cursor(self, handle_name: Optional[str]):
        w: RouterCanvas = self.widget
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
