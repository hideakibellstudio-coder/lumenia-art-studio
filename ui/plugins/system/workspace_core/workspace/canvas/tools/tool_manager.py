"""ToolManager — Centralized Life-Cycle Manager for Canvas Tools.

Manages instantiation, state transitions, and high-level operations for
selection, shape, transform, eyedropper, geometry, and text tools.
Strictly decoupled in compliance with ARCcC v2 (< 200 LOC).
"""

from typing import Any, Optional, Protocol, runtime_checkable

from PySide6 import QtGui

from ui.core.engine.registry import EngineRegistry
from ui.core.state import GeometryState
from ui.core.tool_settings import default_tool_settings, normalize_tool_settings
from ui.core.tools import ToolCommand

from .selection_tool_controller import SelectionToolController
from .shape_tool_controller import ShapeToolController
from .transform_tool_controller import TransformToolController
from .eyedrop_tool_controller import EyedropToolController
from .geometry_tool_controller import GeometryToolController
from .text_tool_controller import TextToolController



@runtime_checkable
class ToolCanvas(Protocol):
    """O que o gerenciador de ferramentas usa do canvas (os controladores que ele
    cria recebem o mesmo canvas).

    Até 2026-09-25 este arquivo importava o `RenderWidget` da pasta mãe só
    para anotar tipo (o ciclo canvas ↔ tools). Membro novo usado aqui entra
    neste contrato; `tests/test_canvas_contracts.py` confere que o
    `RenderWidget` o cumpre.
    """
    active_color: QtGui.QColor
    strokeStarted: Any
    strokeFinished: Any

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> Any: ...
    def update(self) -> None: ...


class ToolManager:
    """Coordinates canvas tool controllers, settings, and command dispatch."""

    def __init__(self, widget: ToolCanvas, geometry_state: Optional[GeometryState] = None) -> None:
        self.widget = widget

        self.selection_ctrl = SelectionToolController(widget)
        self.shape_ctrl = ShapeToolController(widget)
        self.transform_ctrl = TransformToolController(widget)
        self.eyedrop_ctrl = EyedropToolController(widget)
        self.geometry_ctrl = GeometryToolController(widget, geometry_state)
        self.text_ctrl = TextToolController(widget)
        # O balde não tem controlador próprio: as opções dele moram aqui.
        self.bucket_settings = default_tool_settings("bucket")

    # ── Opções de ferramenta (vindas do ToolState) ──
    def apply_tool_settings(self, key: str, settings: dict) -> None:
        """Entrega opções já normalizadas ao controlador que as consome.

        `key` é a chave de opções do ToolState (`ui.core.state.options_key`).
        Único ponto de entrada de opções no canvas: antes de 2026-09-24 o
        workspace escrevia direto nos dicionários `canvas._bucket_settings`,
        `canvas._wand_settings`...
        """
        if key == "eyedrop":
            self.eyedrop_ctrl.settings.update(settings)
        elif key == "bucket":
            self.bucket_settings.update(settings)
        elif key == "wand":
            self.selection_ctrl.wand_settings.update(settings)
        elif key in ("rect_select", "ellipse_select"):
            self.selection_ctrl.geom_select_settings.update(settings)
        elif key == "lasso":
            self.selection_ctrl.lasso_settings.update(settings)
        elif key == "shapes":
            self.set_shape_settings(settings)
        elif key == "text":
            self.set_text_settings(settings)
        elif key == "transform":
            self.transform_ctrl.interp_mode = settings["interp_mode"]
            self.transform_ctrl.lock_aspect = settings["lock_aspect"]
            self.transform_ctrl.distort = settings["distort"]
        # "smudge": parâmetros do perfil nativo do pincel, aplicados ao motor
        # pela barra secundária; o canvas não os usa.

    def run_command(self, command: ToolCommand) -> None:
        """Executa um comando pontual vindo de um botão (ver `ui.core.tools.ToolCommand`)."""
        actions = {
            ToolCommand.DESELECT: self.selection_ctrl.clear_selection,
            ToolCommand.TRANSFORM_COMMIT: self.commit_transform,
            ToolCommand.TRANSFORM_CANCEL: self.cancel_transform,
            ToolCommand.TRANSFORM_FLIP_H: self.transform_flip_h,
            ToolCommand.TRANSFORM_FLIP_V: self.transform_flip_v,
            ToolCommand.TRANSFORM_ROTATE_90: self.transform_rotate_90,
            ToolCommand.TEXT_COMMIT: self.commit_text_overlay,
            ToolCommand.TEXT_CANCEL: self.cancel_text_overlay,
        }
        actions[ToolCommand(command)]()

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
        try:
            b = EngineRegistry.instance().get_backend()
            if b:
                opts = self.bucket_settings
                ok = b.fill_area(
                    seed_x=int(evt.x),
                    seed_y=int(evt.y),
                    fill_color=self.widget.active_color,
                    tolerance=opts["tolerance"],
                    contiguous=opts["contiguous"],
                    expand_px=opts["expand_px"],
                    sample_all=opts["sample_all"],
                )
                if ok:
                    self.widget.update()
        finally:
            self.widget.strokeFinished.emit()

    def clear_canvas(self) -> None:
        self.widget.strokeStarted.emit()
        try:
            b = EngineRegistry.instance().get_backend()
            if b:
                b.clear_canvas()
            self.shape_ctrl.drag_active = False
            self.widget.update()
        finally:
            self.widget.strokeFinished.emit()
