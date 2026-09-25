"""Camera and Viewport 2D Navigation Controller."""

from PySide6 import QtCore, QtGui
from ui.core.engine.backend import PointerEvent

class CameraController:
    """Controlador 2D de Câmera, Matriz de Visualização e Mapeamento de Coordenadas."""

    def __init__(self, widget):
        self.widget = widget
        self.zoom: float = 1.0
        self.pan_x: float = 0.0
        self.pan_y: float = 0.0
        self.rotation: float = 0.0
        self.flip_horizontal: bool = False
        self.flip_vertical: bool = False

    def get_canvas_transform(self, canvas_w: int, canvas_h: int) -> QtGui.QTransform:
        """Calcula a matriz 2D de transformação (Translate -> Rotate -> Scale -> Flip -> Offset)."""
        w = float(self.widget.width())
        h = float(self.widget.height())

        transform = QtGui.QTransform()
        transform.translate(w / 2.0 + self.pan_x, h / 2.0 + self.pan_y)
        transform.rotate(self.rotation)
        
        sx = -self.zoom if self.flip_horizontal else self.zoom
        sy = -self.zoom if self.flip_vertical else self.zoom
        transform.scale(sx, sy)

        transform.translate(-float(canvas_w) / 2.0, -float(canvas_h) / 2.0)
        return transform

    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float, canvas_w: int, canvas_h: int) -> PointerEvent:
        """Mapeia coordenadas da tela do widget para o espaço interno do canvas (0..w, 0..h)."""
        transform = self.get_canvas_transform(canvas_w, canvas_h)
        inv, ok = transform.inverted()
        if ok:
            pt = inv.map(QtCore.QPointF(screen_x, screen_y))
            return PointerEvent(x=pt.x(), y=pt.y(), pressure=pressure, timestamp=timestamp)
        return PointerEvent(x=screen_x, y=screen_y, pressure=pressure, timestamp=timestamp)

    def center_canvas(self, canvas_w: int, canvas_h: int):
        w = max(1, self.widget.width())
        h = max(1, self.widget.height())
        scale_x = w / float(max(1, canvas_w))
        scale_y = h / float(max(1, canvas_h))
        self.zoom = min(scale_x, scale_y) * 0.8
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.rotation = 0.0
        self.flip_horizontal = False
        self.flip_vertical = False

    def reset_view(self, canvas_w: int, canvas_h: int):
        self.center_canvas(canvas_w, canvas_h)

    def zoom_at(self, factor: float, anchor_x: float, anchor_y: float, canvas_w: int, canvas_h: int):
        old_zoom = self.zoom
        new_zoom = max(0.02, min(64.0, old_zoom * factor))
        if abs(new_zoom - old_zoom) < 1e-6:
            return

        # Zoom com ponto âncora no cursor
        w = float(self.widget.width())
        h = float(self.widget.height())
        cx = w / 2.0 + self.pan_x
        cy = h / 2.0 + self.pan_y

        ratio = new_zoom / old_zoom
        self.pan_x = (self.pan_x - (anchor_x - cx)) * ratio + (anchor_x - cx)
        self.pan_y = (self.pan_y - (anchor_y - cy)) * ratio + (anchor_y - cy)
        self.zoom = new_zoom
