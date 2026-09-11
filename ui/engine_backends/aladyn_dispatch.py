"""Dispatch canonical commands through the same public backend operations."""

from ui.core.engine import commands as cmd


def dispatch(backend, command):
    if not backend.available:
        raise RuntimeError("motor de pintura indisponível")
    if isinstance(command, cmd.StartStrokeCommand):
        backend.start_stroke(command.x, command.y, command.pressure)
    elif isinstance(command, cmd.DrawCommand):
        backend.paint_stroke(command.x, command.y, command.pressure, command.timestamp)
    elif isinstance(command, cmd.EndStrokeCommand):
        backend.end_stroke()
    elif isinstance(command, cmd.ClearCommand):
        backend.clear_canvas()
    elif isinstance(command, cmd.SetBrushColorCommand):
        backend.set_brush_color(command.r, command.g, command.b)
    elif isinstance(command, cmd.SetBrushSizeCommand):
        backend.set_brush_size(command.size)
    elif isinstance(command, cmd.SetBrushOpacityCommand):
        backend.set_brush_opacity(command.opacity)
    elif isinstance(command, cmd.SetBrushSpacingCommand):
        backend.set_brush_spacing(command.spacing)
    else:
        raise TypeError(f"comando não suportado: {type(command).__name__}")
