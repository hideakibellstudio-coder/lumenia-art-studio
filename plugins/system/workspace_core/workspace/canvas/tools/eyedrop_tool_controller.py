"""Eyedropper Tool and Color Sampling Controller."""

from PySide6 import QtCore, QtGui

class EyedropToolController:
    """Controlador de amostragem de cor e HUD de lupa do Conta-Gotas."""

    def __init__(self, widget):
        self.widget = widget
        self.active: bool = False
        self.pos: QtCore.QPointF = QtCore.QPointF()
        self.old_color: QtGui.QColor = QtGui.QColor(0, 0, 0)
        self.current_color: QtGui.QColor = QtGui.QColor(0, 0, 0)
        self.settings: dict = {
            "sample_size": "1x1 Ponto Único",
            "sample_radius": 0,
            "sample_all": True,
            "show_loupe": True,
        }

    def do_sample(self, screen_x: float, screen_y: float) -> QtGui.QColor:
        world_evt = self.widget.to_canvas(screen_x, screen_y, 1.0, 0.0)
        wx = int(max(0, min(self.widget.canvas_w - 1, world_evt.x)))
        wy = int(max(0, min(self.widget.canvas_h - 1, world_evt.y)))

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
