"""
CompactSlider  (portado de BrushC — CompactValueSliderWidget)
──────────────────────────────────────────────────────────────
Slider inline que preenche seu fundo proporcionalmente ao valor.
Drag horizontal muda o valor. Visual estilo Blender / Krita com suporte a temas.
"""
from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.theme.manager import ThemeManager


class CompactSlider(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(int)

    def __init__(self, prefix: str = "", min_val: int = 0,
                 max_val: int = 100, unit: str = "", parent=None):
        super().__init__(parent)
        self.prefix   = prefix
        self._min     = min_val
        self._max     = max_val
        self._value   = min_val
        self.unit     = unit

        self.setMinimumHeight(20)
        self.setMaximumHeight(22)
        self.setCursor(QtCore.Qt.SplitHCursor)

        # Configura cores dinâmicas via ThemeManager
        ThemeManager.instance().themeChanged.connect(self._update_theme)
        self._update_theme("")

    def _update_theme(self, *args):
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_panel", "#1e1e24")
        border = tm.get_color("border", "#2e2e38")
        accent = tm.get_color("accent", "#6366f1")
        text = tm.get_color("text_main", "#f3f4f6")
        self.apply_theme(bg, border, accent, text)

    # ── Value API ─────────────────────────────────────────────────────
    def setValue(self, val: int):
        val = max(self._min, min(self._max, int(val)))
        if val != self._value:
            self._value = val
            self.update()

    def value(self) -> int:
        return self._value

    def apply_theme(self, bg: str, border: str, accent: str, text: str):
        self._bg     = QtGui.QColor(bg)
        self._border = QtGui.QColor(border)
        self._accent = QtGui.QColor(accent)
        self._text   = QtGui.QColor(text)
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self.rect()
        w, h = r.width(), r.height()

        # Background
        p.setPen(QtGui.QPen(self._border, 1))
        p.setBrush(QtGui.QBrush(self._bg))
        p.drawRoundedRect(0, 0, w - 1, h - 1, 3, 3)

        # Fill bar
        frac = (self._value - self._min) / max(1, self._max - self._min)
        fill_w = int((w - 2) * frac)
        if fill_w > 0:
            fill_col = QtGui.QColor(self._accent)
            fill_col.setAlpha(90)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QBrush(fill_col))
            p.drawRoundedRect(1, 1, fill_w, h - 2, 2, 2)

        # Text
        txt = f"{self.prefix} {self._value}{self.unit}".strip()
        p.setPen(self._text)
        p.setFont(QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold))
        p.drawText(r, QtCore.Qt.AlignCenter, txt)
        p.end()

    # ── Drag interaction ──────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_x   = event.pos().x()
            self._drag_start_val = self._value

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            dx    = event.pos().x() - self._drag_start_x
            range = max(1, self._max - self._min)
            step  = (range / float(self.width())) * dx
            new_val = int(self._drag_start_val + step)
            self.setValue(new_val)
            self.valueChanged.emit(self._value)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.valueChanged.emit(self._value)
