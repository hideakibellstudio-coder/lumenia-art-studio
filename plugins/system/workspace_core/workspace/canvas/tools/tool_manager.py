"""ToolManager — Centralized Life-Cycle Manager for Canvas Tools.

Manages instantiation, state transitions, and high-level operations for
selection, shape, transform, eyedropper, geometry, and text tools.
Strictly decoupled in compliance with ARCcC v2 (< 200 LOC).
"""

from typing import TYPE_CHECKING
from PySide6 import QtGui

from ui.core.engine.registry import EngineRegistry
from ui.core.tool_settings import normalize_tool_settings

from .selection_tool_controller import SelectionToolController
from .shape_tool_controller import ShapeToolController
from .transform_tool_controller import TransformToolController
from .eyedrop_tool_controller import EyedropToolController
from .geometry_tool_controller import GeometryToolController
from .text_tool_controller import TextToolController

if TYPE_CHECKING:
    from ..render_widget import RenderWidget


class ToolManager:
    """Coordinates canvas tool controllers, settings, and command dispatch."""

    def __init__(self, widget: 'RenderWidget') -> None:
        self.widget = widget

        self.selection_ctrl = SelectionToolController(widget)
        self.shape_ctrl = ShapeToolController(widget)
        self.transform_ctrl = TransformToolController(widget)
        self.eyedrop_ctrl = EyedropToolController(widget)
        self.geometry_ctrl = GeometryToolController(widget)
        self.text_ctrl = TextToolController(widget)

    # ── Transform Tool Commands ──
    def start_transform_mode(self) -> bool:
        return self.transform_ctrl.start_mode()

    def commit_transform(self) -> None:
        self.transform_ctrl.commit()

    def cancel_transform(self) -> None:
        self.transform_ctrl.cancel()

    def transform_flip_h(self) -> None:
        self.transform_ctrl.flip_horizontal()

    def transform_flip_v(self) -> None:
        self.transform_ctrl.flip_vertical()

    def transform_rotate_90(self, clockwise: bool = True) -> None:
        self.transform_ctrl.rotate_90(clockwise)

    # ── Shape Tool Commands ──
    def set_shape_settings(self, settings: dict) -> None:
        self.shape_ctrl.settings = normalize_tool_settings("shapes", settings, self.shape_ctrl.settings)
        if self.widget.active_tool == "shapes" or self.widget.active_tool.startswith("shape_"):
            self.widget.active_tool = "shapes"
        self.widget.update()

    # ── Text Tool Commands ──
    @property
    def active_text_editor(self):
        return self.text_ctrl.active_editor

    @active_text_editor.setter
    def active_text_editor(self, val):
        self.text_ctrl.active_editor = val

    @property
    def text_settings(self) -> dict:
        return self.text_ctrl.settings

    @text_settings.setter
    def text_settings(self, val: dict):
        self.text_ctrl.settings = val

    def set_text_settings(self, settings: dict) -> None:
        self.text_ctrl.set_settings(settings)

    def open_text_editor(self, canvas_x: float, canvas_y: float) -> None:
        self.text_ctrl.open_editor(canvas_x, canvas_y)

    def commit_text_overlay(self) -> None:
        self.text_ctrl.commit()

    def cancel_text_overlay(self) -> None:
        self.text_ctrl.cancel()

    # ── Bucket / Flood Fill Commands ──
    def do_flood_fill(self, screen_x: float, screen_y: float) -> None:
        evt = self.widget.to_canvas(screen_x, screen_y, 1.0, 0.0)
        self.widget.strokeStarted.emit()
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "fill_area"):
            ok = b.fill_area(
                seed_x=int(evt.x),
                seed_y=int(evt.y),
                fill_color=getattr(self.widget, "_active_draw_color", QtGui.QColor(0, 0, 0, 255)),
                tolerance=self.widget._bucket_settings.get("tolerance", 20),
                contiguous=self.widget._bucket_settings.get("contiguous", True),
                expand_px=self.widget._bucket_settings.get("expand_px", 1),
                gap_closing_px=self.widget._bucket_settings.get("gap_closing_px", 0),
                aa=self.widget._bucket_settings.get("aa", True),
                sample_all=self.widget._bucket_settings.get("sample_all", True)
            )
            if ok:
                self.widget.update()
                self.widget.strokeFinished.emit()

    def clear_canvas(self) -> None:
        b = EngineRegistry.instance().get_backend()
        if b and hasattr(b, "clear_canvas"):
            b.clear_canvas()
        self.widget._flood_layers.clear()
        self.widget._flood_redo_stack.clear()
        self.shape_ctrl.drag_active = False
        self.widget.update()
