from PySide6 import QtWidgets, QtCore, QtGui, QtSvg
from ui.core.theme.manager import ThemeManager


def make_svg_minus_icon(color_hex: str = "#f3f4f6") -> bytes:
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="{color_hex}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
        <line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>'''
    return svg_data.encode('utf-8')


def make_svg_plus_icon(color_hex: str = "#f3f4f6") -> bytes:
    svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="{color_hex}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="5" x2="12" y2="19"></line>
        <line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>'''
    return svg_data.encode('utf-8')


class SliderStepButton(QtWidgets.QAbstractButton):
    """
    Botão de acessibilidade para sliders com ícone SVG de decremento (-) ou incremento (+).
    - style_type="square": formato quadrado com border-radius 3px (Captura 1 - CompactSlider)
    - style_type="round": formato circular (Captura 2 - LabeledSlider)
    """
    def __init__(self, is_plus: bool = False, style_type: str = "square", size: int = 20, parent=None):
        super().__init__(parent)
        self.is_plus = is_plus
        self.style_type = style_type
        self.btn_size = size
        self.setFixedSize(size, size)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        
        # Habilita disparo contínuo ao pressionar e segurar
        self.setAutoRepeat(True)
        self.setAutoRepeatDelay(300)
        self.setAutoRepeatInterval(50)

        self._hover = False
        self._pressed = False

        ThemeManager.instance().themeChanged.connect(self._update_colors)
        self._update_colors()

    def _update_colors(self, *args):
        tm = ThemeManager.instance()
        self._bg_color = QtGui.QColor(tm.get_color("bg_panel"))
        self._bg_hover_color = QtGui.QColor(tm.get_color("bg_light"))
        self._border_color = QtGui.QColor(tm.get_color("border"))
        self._accent_color = QtGui.QColor(tm.get_color("accent"))
        self._icon_color_str = tm.get_color("text_main")
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._pressed = False
            self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        r = self.rect()

        # Determina a cor de fundo e borda baseada em hover/press/enabled
        if not self.isEnabled():
            bg = self._bg_color.darker(120)
            border = self._border_color.darker(120)
            icon_hex = "#6b7280"
        elif self._pressed:
            bg = QtGui.QColor(self._accent_color)
            bg.setAlpha(180)
            border = self._accent_color
            icon_hex = "#ffffff"
        elif self._hover:
            bg = self._bg_hover_color
            border = self._accent_color
            icon_hex = self._icon_color_str
        else:
            bg = QtGui.QColor(self._bg_color)
            border = QtGui.QColor(self._border_color)
            icon_hex = self._icon_color_str

        p.setPen(QtGui.QPen(border, 1))
        p.setBrush(QtGui.QBrush(bg))

        if self.style_type == "round":
            p.drawEllipse(r.adjusted(1, 1, -1, -1))
        else:
            p.drawRoundedRect(r.adjusted(0, 0, -1, -1), 3, 3)

        # Desenha ícone SVG
        svg_bytes = make_svg_plus_icon(icon_hex) if self.is_plus else make_svg_minus_icon(icon_hex)
        renderer = QtSvg.QSvgRenderer(svg_bytes)
        
        icon_size = max(8, int(r.width() * 0.5))
        margin = (r.width() - icon_size) // 2
        icon_rect = QtCore.QRect(margin, margin, icon_size, icon_size)
        renderer.render(p, QtCore.QRectF(icon_rect))
        p.end()
