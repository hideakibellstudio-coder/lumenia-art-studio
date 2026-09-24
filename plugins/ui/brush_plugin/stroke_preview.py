"""
StrokePreview  (Lumenia V2 High-Fidelity Engine Preview)
────────────────────────────────────────────────────────────────────────
Renderiza a simulação física exata do motor ativo (Pencil, Watercolor,
OilImpasto, Inker, Marker, Blur, Smudge) usando o pipeline C++ nativo.
Fallback gracioso para renderização vetorial caso o nativo esteja indisponível.
"""
import math
from PySide6 import QtWidgets, QtCore, QtGui

from ui.core.engine.registry import EngineRegistry


class StrokePreview(QtWidgets.QWidget):
    DEFAULT_HEIGHT = 52

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self.DEFAULT_HEIGHT)
        self.setMinimumWidth(80)

        # Estado do pincel
        self._engine_type = 0
        self._size     = 40.0
        self._opacity  = 1.0
        self._hardness = 0.85
        self._spacing  = 0.10
        self._pressure = 0.50
        self._color    = [0.0, 0.0, 0.0]
        
        # Parâmetros específicos por mini-motor
        self._watercolor_params = None
        self._oil_params = None
        self._pencil_params = None
        self._inker_params = None
        self._marker_params = None
        self._blur_params = None
        self._smudge_params = None

        self._cached_image = None
        self._dirty = True

    def update_preview(self):
        self._dirty = True
        self.update()

    def update_brush_state(self,
                           size: float = None,
                           opacity: float = None,
                           hardness: float = None,
                           spacing: float = None,
                           pressure: float = None,
                           color: list = None,
                           engine_type: int = None,
                           watercolor_params=None,
                           oil_params=None,
                           pencil_params=None,
                           inker_params=None,
                           marker_params=None,
                           blur_params=None,
                           smudge_params=None):
        """Atualiza os parâmetros de traço e invalida o buffer em cache."""
        if size is not None:     self._size = size
        if opacity is not None:  self._opacity = opacity
        if hardness is not None: self._hardness = hardness
        if spacing is not None:  self._spacing = spacing
        if pressure is not None: self._pressure = pressure
        if color is not None:    self._color = color
        if engine_type is not None: self._engine_type = engine_type
        if watercolor_params is not None: self._watercolor_params = watercolor_params
        if oil_params is not None: self._oil_params = oil_params
        if pencil_params is not None: self._pencil_params = pencil_params
        if inker_params is not None: self._inker_params = inker_params
        if marker_params is not None: self._marker_params = marker_params
        if blur_params is not None: self._blur_params = blur_params
        if smudge_params is not None: self._smudge_params = smudge_params

        self._dirty = True
        self.update()

    def _render_native_preview(self, w: int, h: int) -> QtGui.QImage:
        backend = EngineRegistry.instance().get_backend()
        if not backend or not hasattr(backend, "render_brush_preview"):
            return None

        try:
            state = {
                "size": self._size,
                "opacity": self._opacity,
                "hardness": self._hardness,
                "spacing": self._spacing,
                "pressure": self._pressure,
                "color": self._color,
                "engine_type": self._engine_type,
                "watercolor_params": self._watercolor_params,
                "oil_params": self._oil_params,
                "pencil_params": self._pencil_params,
                "inker_params": self._inker_params,
                "marker_params": self._marker_params,
                "blur_params": self._blur_params,
                "smudge_params": self._smudge_params,
            }
            raw_bytes = backend.render_brush_preview(w, h, state)
            if raw_bytes and len(raw_bytes) == w * h * 4:
                img = QtGui.QImage(raw_bytes, w, h, w * 4, QtGui.QImage.Format_RGBA8888)
                return img.copy()  # Cópia segura
        except Exception:
            return None

        return None

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        w, h = max(10, self.width()), max(10, self.height())

        # 1. Fundo quadriculado (Checkerboard)
        p.fillRect(self.rect(), QtCore.Qt.white)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(225, 225, 225))
        sq = 8
        for x in range(0, w, sq):
            for y in range(0, h, sq):
                if (x // sq + y // sq) % 2 == 1:
                    p.drawRect(x, y, sq, sq)

        # 2. Renderização do traço nativo
        if self._dirty or self._cached_image is None or self._cached_image.width() != w or self._cached_image.height() != h:
            native_img = self._render_native_preview(w, h)
            if native_img:
                self._cached_image = native_img
                self._dirty = False
            else:
                self._cached_image = None

        if self._cached_image:
            p.drawImage(0, 0, self._cached_image)
        else:
            # Fallback vetorial
            margin = 10
            amp = (h / 2) - margin
            c = self._color
            base_color = QtGui.QColor(int(c[0] * 255), int(c[1] * 255), int(c[2] * 255))
            img = QtGui.QImage(self.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
            img.fill(QtCore.Qt.transparent)
            ip = QtGui.QPainter(img)
            ip.setRenderHint(QtGui.QPainter.Antialiasing)
            ip.setPen(QtCore.Qt.NoPen)
            step_px = max(1.0, self._size * self._spacing)
            x_pos = float(margin)
            usable_width = float(w - 2 * margin)
            while x_pos < (w - margin):
                t = (x_pos - margin) / usable_width if usable_width > 0 else 0.0
                y = h / 2 + math.sin(t * math.pi * 2) * amp * 0.65
                pressure_sim = self._pressure * (0.3 + 0.7 * math.sin(t * math.pi))
                r = max(0.5, (self._size * pressure_sim) / 2.0)
                grad = QtGui.QRadialGradient(QtCore.QPointF(x_pos, y), r)
                alpha = int(self._opacity * 255)
                stop = max(0.01, min(0.99, self._hardness))
                grad.setColorAt(0, QtGui.QColor(base_color.red(), base_color.green(), base_color.blue(), alpha))
                grad.setColorAt(stop, QtGui.QColor(base_color.red(), base_color.green(), base_color.blue(), alpha))
                grad.setColorAt(1.0, QtGui.QColor(base_color.red(), base_color.green(), base_color.blue(), 0))
                ip.setBrush(grad)
                ip.drawEllipse(QtCore.QPointF(x_pos, y), r, r)
                x_pos += step_px
            ip.end()
            p.drawImage(0, 0, img)

        # 3. Contorno visual arredondado do widget
        p.setPen(QtGui.QPen(QtGui.QColor(128, 128, 128, 60), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)
        p.end()
