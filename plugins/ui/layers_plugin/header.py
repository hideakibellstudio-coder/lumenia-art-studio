from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSizePolicy
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont

class LayersOpacitySliderWidget(QWidget):
    """
    Slider customizado para opacidade de camadas no estilo blend box.
    Retorna valor de 0 a 100 com preenchimento da cor ACCENT.
    """
    valueChanged = Signal(int)
    sliderPressed = Signal()
    sliderReleased = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 100
        self.setMinimumHeight(22)
        self.setMaximumHeight(26)
        self.setCursor(Qt.SplitHCursor)

        from ui.core.theme.manager import ThemeManager
        theme = ThemeManager.instance()._themes.get(ThemeManager.instance().current_theme, {})
        colors = theme.get("colors", {})

        self._bg_color = QColor(ThemeManager.instance().resolve_color("bg_panel", colors))
        self._border_color = QColor(ThemeManager.instance().resolve_color("border", colors))
        self._accent_color = QColor(ThemeManager.instance().resolve_color("ACCENT", colors))
        self._text_color = QColor(ThemeManager.instance().resolve_color("text_main", colors))

    def setValue(self, val):
        val = max(0, min(100, int(val)))
        if val != self._value:
            self._value = val
            self.update()

    def value(self):
        return self._value

    def set_theme_colors(self, bg_color, border_color, accent_color, text_color):
        self._bg_color = QColor(bg_color)
        self._border_color = QColor(border_color)
        self._accent_color = QColor(accent_color)
        self._text_color = QColor(text_color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        r = self.rect()
        w = r.width()
        h = r.height()

        painter.setPen(QPen(self._border_color, 1))
        painter.setBrush(QBrush(self._bg_color))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 4, 4)

        fill_w = int((self._value / 100.0) * (w - 2))
        if fill_w > 0:
            painter.setClipRect(1, 1, w - 2, h - 2)
            fill_color = QColor(self._accent_color)
            fill_color.setAlpha(120)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(fill_color))
            painter.drawRoundedRect(1, 1, fill_w, h - 2, 3, 3)
            painter.setClipping(False)

        painter.setPen(self._text_color)
        font = painter.font()
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)

        text = f"Opacidade: {self._value}%"
        painter.drawText(r, Qt.AlignCenter, text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.sliderPressed.emit()
            self._update_value_from_pos(event.position().x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.sliderReleased.emit()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._update_value_from_pos(event.position().x())

    def _update_value_from_pos(self, x):
        w = self.width()
        if w > 0:
            val = int(max(0, min(100, (x / w) * 100)))
            if val != self._value:
                self._value = val
                self.valueChanged.emit(val)
                self.update()


class LayersHeader(QWidget):
    opacityChanged = Signal(int)
    blendModeChanged = Signal(str)
    opacitySliderPressed = Signal()
    opacitySliderReleased = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        layout.setSpacing(6)

        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(0, 0, 0, 0)
        ctrl_row.setSpacing(6)

        self.combo_blend = QComboBox()
        self.combo_blend.setObjectName("LayersBlendCombo")
        self._all_blend_modes = [
            "Normal",
            "Atravessar",
            "Multiplicação",
            "Divisão",
            "Sobreposição",
            "Escurecer",
            "Clarear",
            "Borracha"
        ]
        self.combo_blend.addItems(self._all_blend_modes)
        self.combo_blend.setToolTip("Modo de Mesclagem da Camada")
        self.combo_blend.setMinimumWidth(95)
        self.combo_blend.setMaximumWidth(115)
        self.combo_blend.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.combo_blend.currentTextChanged.connect(self.blendModeChanged.emit)

        self.slider_op = LayersOpacitySliderWidget()
        self.slider_op.setObjectName("LayersOpacitySlider")
        self.slider_op.setValue(100)
        self.slider_op.setToolTip("Opacidade (0–100%)")
        self.slider_op.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider_op.valueChanged.connect(self.opacityChanged.emit)
        self.slider_op.sliderPressed.connect(self.opacitySliderPressed.emit)
        self.slider_op.sliderReleased.connect(self.opacitySliderReleased.emit)

        ctrl_row.addWidget(self.combo_blend, 0)
        ctrl_row.addWidget(self.slider_op, 1)
        layout.addLayout(ctrl_row)

    def set_values(self, opacity, blend_mode, is_group=False):
        self.slider_op.blockSignals(True)
        self.combo_blend.blockSignals(True)
        try:
            val = int(opacity * 100 if isinstance(opacity, float) and opacity <= 1.0 else opacity)
            self.slider_op.setValue(val)

            if is_group:
                if "Atravessar" not in [self.combo_blend.itemText(i) for i in range(self.combo_blend.count())]:
                    self.combo_blend.insertItem(1, "Atravessar")
            else:
                idx = self.combo_blend.findText("Atravessar")
                if idx >= 0:
                    self.combo_blend.removeItem(idx)

            idx = self.combo_blend.findText(blend_mode)
            if idx >= 0:
                self.combo_blend.setCurrentIndex(idx)
        finally:
            self.slider_op.blockSignals(False)
            self.combo_blend.blockSignals(False)

    def on_theme_changed(self, colors):
        bg_input = colors.get("bg_panel", "#1f2937")
        border = colors.get("border", "#374151")
        accent = colors.get("ACCENT", "#3b82f6")
        text_primary = colors.get("text_main", "#f3f4f6")

        self.slider_op.set_theme_colors(
            bg_color=bg_input,
            border_color=border,
            accent_color=accent,
            text_color=text_primary
        )

        sheet = f"""
            QComboBox#LayersBlendCombo {{
                background-color: {bg_input};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 500;
            }}
            QComboBox#LayersBlendCombo:hover {{
                border-color: {accent};
            }}
            QComboBox#LayersBlendCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 16px;
                border-left-width: 0px;
            }}
            QComboBox#LayersBlendCombo QAbstractItemView {{
                background-color: {bg_input};
                color: {text_primary};
                selection-background-color: {accent};
                selection-color: #ffffff;
                border: 1px solid {border};
                outline: none;
            }}
        """
        self.combo_blend.setStyleSheet(sheet)
