"""
ui.core.plugins.contracts — Contratos de comandos do motor (casca limp)
=======================================================================
Reexporta os comandos de motor como DATACLASSES PURAS (ui.core.engine.commands)
em vez das classes PyO3 do binário `engine_core`.

Isso permite que a casca, dispatcher e plugins operem sem qualquer binário
de motor compilado — o motor é apenas um backend plugável.
"""

from ui.core.engine.commands import (
    DrawCommand,
    StartStrokeCommand,
    EndStrokeCommand,
    ClearCommand,
    SetBrushColorCommand,
    SetBrushSizeCommand,
    SetBrushOpacityCommand,
    SetBrushSpacingCommand,
)

__all__ = [
    "DrawCommand", "StartStrokeCommand", "EndStrokeCommand", "ClearCommand",
    "SetBrushColorCommand", "SetBrushSizeCommand", "SetBrushOpacityCommand", "SetBrushSpacingCommand",
]
