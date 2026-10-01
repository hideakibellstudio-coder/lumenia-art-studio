"""Eyedropper Tool and Color Sampling Controller."""

from typing import Any, Optional, Protocol, runtime_checkable

from PySide6 import QtCore, QtGui
from ui.core.engine.backend_protocols import ColorProtocol, LayerProtocol
from ui.core.tool_settings import default_tool_settings


class EyedropEngine(ColorProtocol, LayerProtocol, Protocol):
    """A amostra vem do motor (`Color`), da camada ativa quando "todas as camadas" está desligado (`Layer`)."""


@runtime_checkable
class EyedropCanvas(Protocol):
    """O que o conta-gotas usa do canvas. Membro novo usado aqui entra neste contrato;
    `tests/test_canvas_contracts.py` confere que o `RenderWidget` o cumpre."""
    canvas_w: int
    canvas_h: int
    backend: Optional[EyedropEngine]
    colorPicked: Any

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> Any: ...
    def get_canvas_image(self, apply_proofing: bool = True) -> Any: ...


class EyedropToolController:
    """Controlador de amostragem de cor e HUD de lupa do Conta-Gotas."""

    def __init__(self, widget: EyedropCanvas):
        self.widget = widget
        self.active: bool = False
        self.pos: QtCore.QPointF = QtCore.QPointF()
        self.old_color: QtGui.QColor = QtGui.QColor(0, 0, 0)
        self.current_color: QtGui.QColor = QtGui.QColor(0, 0, 0)
        self.settings = default_tool_settings("eyedrop")

    def do_sample(self, screen_x: float, screen_y: float) -> QtGui.QColor:
        world_evt = self.widget.to_canvas(screen_x, screen_y, 1.0, 0.0)
        wx = int(max(0, min(self.widget.canvas_w - 1, world_evt.x)))
        wy = int(max(0, min(self.widget.canvas_h - 1, world_evt.y)))

        # Delegate sampling to the backend when available so the “all layers”
        # option has real semantics and matches the native compositor.
        backend = self.widget.backend
        if backend is not None:
            radius = int(self.settings.get("sample_radius", 0))
            try:
                if self.settings.get("sample_all", True):
                    rgba = backend.pick_color_merged(wx, wy, radius)
                else:
                    layer_index = int(backend.get_active_layer_index())
                    rgba = backend.pick_color_layer(layer_index, wx, wy, radius)
                if rgba and len(rgba) >= 4:
                    col = QtGui.QColor(*[int(max(0, min(255, c))) for c in rgba[:4]])
                    self.current_color = col
                    self.widget.colorPicked.emit(col)
                    return col
            except (AttributeError, TypeError, ValueError, RuntimeError):
                # Keep the QImage fallback for alternate backends.
                pass

        composite = self.widget.get_canvas_image()
        if not composite or composite.isNull():
            return QtGui.QColor(0, 0, 0)

        radius = int(self.settings.get("sample_radius", 0))

        if radius <= 0:
            col = composite.pixelColor(wx, wy)
        else:
            r_acc, g_acc, b_acc, a_acc, count = 0, 0, 0, 0, 0
            x_min = max(0, wx - radius)
            x_max = min(self.widget.canvas_w - 1, wx + radius)
            y_min = max(0, wy - radius)
            y_max = min(self.widget.canvas_h - 1, wy + radius)

            for py in range(y_min, y_max + 1):
                for px in range(x_min, x_max + 1):
                    p_col = composite.pixelColor(px, py)
                    r_acc += p_col.red()
                    g_acc += p_col.green()
                    b_acc += p_col.blue()
                    a_acc += p_col.alpha()
                    count += 1

            if count > 0:
                col = QtGui.QColor(
                    int(r_acc / count),
                    int(g_acc / count),
                    int(b_acc / count),
                    int(a_acc / count),
                )
            else:
                col = composite.pixelColor(wx, wy)

        self.current_color = col
        self.widget.colorPicked.emit(col)
        return col
