"""Views de opções por ferramenta da barra secundária (uma por orientação).

Porta de entrada: `build_option_views(tool_state, brush_state, orientation)`
devolve `{chave de opções: view}`. A chave é a do `ToolState`
(`ui.core.state.options_key`): todas as `shape_*` usam "shapes".
"""
from __future__ import annotations

from PySide6 import QtCore

from ui.core.state import BrushState, ToolState

from .base import OrientedOptionsView
from .eyedrop_transform_views import EyedropOptionsView, TransformOptionsView
from .fill_views import BucketOptionsView, WandOptionsView
from .selection_view import SelectionOptionsView
from .shapes_view import ShapesOptionsView
from .smudge_view import SmudgeOptionsView
from .text_view import TextOptionsView


def build_option_views(
    tool_state: ToolState, brush_state: BrushState, orientation: QtCore.Qt.Orientation
) -> dict[str, OrientedOptionsView]:
    return {
        "eyedrop": EyedropOptionsView(tool_state, brush_state, orientation),
        "bucket": BucketOptionsView(tool_state, orientation),
        "wand": WandOptionsView(tool_state, orientation),
        "rect_select": SelectionOptionsView(tool_state, "rect_select", orientation),
        "ellipse_select": SelectionOptionsView(tool_state, "ellipse_select", orientation),
        "lasso": SelectionOptionsView(tool_state, "lasso", orientation),
        "transform": TransformOptionsView(tool_state, orientation),
        "smudge": SmudgeOptionsView(tool_state, orientation),
        "shapes": ShapesOptionsView(tool_state, orientation),
        "text": TextOptionsView(tool_state, orientation),
    }


__all__ = ["OrientedOptionsView", "build_option_views"]
