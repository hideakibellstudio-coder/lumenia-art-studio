"""
CompactSlider (com botões de acessibilidade (-) e (+) no visual quadrado - Captura 1)
──────────────────────────────────────────────────────────────
Slider inline preenchido proporcionalmente ao valor com botões laterais de passo.
Drag horizontal muda o valor e cliques nos botões alteram passo a passo.
"""
from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.theme.manager import ThemeManager
from ui.core.widgets.slider.step_button import SliderStepButton


class _CompactSliderCore(QtWidgets.QWidget):
    """
    Sub-widget interno que desenha a barra de preenchimento e o texto do CompactSlider.
    """
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

        ThemeManager.instance().themeChanged.connect(self._update_theme)
        self._update_theme("")

    def _update_theme(self, *args):
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_panel", "#1e1e24")
        border = tm.get_color("border", "#2e2e38")
        accent = tm.get_color("accent", "#6366f1")
        text = tm.get_color("text_main", "#f3f4f6")
        self.apply_theme(bg, border, accent, text)

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

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self.rect()
        w, h = r.width(), r.height()

        p.setPen(QtGui.QPen(self._border, 1))
        p.setBrush(QtGui.QBrush(self._bg))
        p.drawRoundedRect(0, 0, w - 1, h - 1, 3, 3)

        frac = (self._value - self._min) / max(1, self._max - self._min)
        fill_w = int((w - 2) * frac)
        if fill_w > 0:
            fill_col = QtGui.QColor(self._accent)
            fill_col.setAlpha(90)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QBrush(fill_col))
            p.drawRoundedRect(1, 1, fill_w, h - 2, 2, 2)

        txt = f"{self.prefix} {self._value}{self.unit}".strip()
        p.setPen(self._text)
        p.setFont(QtGui.QFont("Segoe UI", 8, QtGui.QFont.Bold))
        p.drawText(r, QtCore.Qt.AlignCenter, txt)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_x   = event.pos().x()
            self._drag_start_val = self._value

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            dx    = event.pos().x() - self._drag_start_x
            range_val = max(1, self._max - self._min)
            step  = (range_val / float(max(1, self.width()))) * dx
            new_val = int(self._drag_start_val + step)
            self.setValue(new_val)
            self.valueChanged.emit(self._value)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.valueChanged.emit(self._value)


class CompactSlider(QtWidgets.QWidget):
    """
    Slider compacto preenchido com botões laterais de acessibilidade (-) e (+) no visual quadrado (Captura 1).
    """
    valueChanged = QtCore.Signal(int)

    def __init__(self, prefix: str = "", min_val: int = 0,
                 max_val: int = 100, unit: str = "", parent=None, step: int = 1):
        super().__init__(parent)
        self._step = step

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self.btn_minus = SliderStepButton(is_plus=False, style_type="square", size=20, parent=self)
        self.btn_plus = SliderStepButton(is_plus=True, style_type="square", size=20, parent=self)

        self.core = _CompactSliderCore(prefix, min_val, max_val, unit, parent=self)
        self.core.valueChanged.connect(self.valueChanged.emit)

        self.btn_minus.clicked.connect(self._decrement)
        self.btn_plus.clicked.connect(self._increment)

        layout.addWidget(self.btn_minus)
        layout.addWidget(self.core, 1)
        layout.addWidget(self.btn_plus)

        self.setMinimumHeight(20)
        self.setMaximumHeight(22)

    def _decrement(self):
        new_val = max(self.core._min, self.core.value() - self._step)
        self.setValue(new_val)
        self.valueChanged.emit(new_val)

    def _increment(self):
        new_val = min(self.core._max, self.core.value() + self._step)
        self.setValue(new_val)
        self.valueChanged.emit(new_val)

    def setValue(self, val: int):
        self.core.setValue(val)

    def value(self) -> int:
        return self.core.value()

    def apply_theme(self, bg: str, border: str, accent: str, text: str):
        self.core.apply_theme(bg, border, accent, text)
