from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSizePolicy
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont

from ui.core.document.layer_blend_mode import LayerBlendMode, DISPLAY_ORDER

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

        self._bg_color = QColor("#1e293b")
        self._border_color = QColor("#334155")
        self._accent_color = QColor("#6366f1")
        self._text_color = QColor("#f3f4f6")

        from ui.infrastructure.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._on_theme_changed)
        self._on_theme_changed()

    def _on_theme_changed(self, *_):
        from ui.infrastructure.theme.manager import ThemeManager
        tm = ThemeManager.instance()
        self._bg_color = QColor(tm.get_color("bg_panel", "#1e293b"))
        self._border_color = QColor(tm.get_color("border", "#334155"))
        self._accent_color = QColor(tm.get_color("accent", "#6366f1"))
        self._text_color = QColor(tm.get_color("text_main", "#f3f4f6"))
        self.update()

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

        from ui.infrastructure.i18n import tr
        text = f"{tr('layers.opacity', 'Opacidade')}: {self._value}%"
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

        from ui.infrastructure.i18n import tr, I18nManager

        self.combo_blend = QComboBox()
        self.combo_blend.setObjectName("LayersBlendCombo")
        # Fonte unica: LayerBlendMode.label (ui/core/document/layer_blend_mode.py).
        # "Atravessar" (PassThrough) fica de fora da lista base -- e' inserida/
        # removida dinamicamente por set_values() conforme a camada ativa e' ou
        # nao um grupo, exatamente como este widget ja fazia antes.
        self._all_blend_modes = [
            m.label for m in DISPLAY_ORDER if m != LayerBlendMode.PASS_THROUGH
        ]
        self.combo_blend.addItems(self._all_blend_modes)
        self.combo_blend.setToolTip(tr("layers.blend_mode", "Modo de Mesclagem da Camada"))
        self.combo_blend.setFixedWidth(102)
        self.combo_blend.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.combo_blend.currentTextChanged.connect(self.blendModeChanged.emit)

        self.slider_op = LayersOpacitySliderWidget()
        self.slider_op.setObjectName("LayersOpacitySlider")
        self.slider_op.setValue(100)
        self.slider_op.setToolTip(f"{tr('layers.opacity', 'Opacidade')} (0–100%)")
        self.slider_op.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider_op.valueChanged.connect(self.opacityChanged.emit)
        self.slider_op.sliderPressed.connect(self.opacitySliderPressed.emit)
        self.slider_op.sliderReleased.connect(self.opacitySliderReleased.emit)

        ctrl_row.addWidget(self.combo_blend, 0)
        ctrl_row.addWidget(self.slider_op, 1)
        layout.addLayout(ctrl_row)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def retranslate_ui(self):
        from ui.infrastructure.i18n import tr
        if hasattr(self, "combo_blend"):
            self.combo_blend.setToolTip(tr("layers.blend_mode", "Modo de Mesclagem da Camada"))
        if hasattr(self, "slider_op"):
            self.slider_op.setToolTip(f"{tr('layers.opacity', 'Opacidade')} (0–100%)")
            self.slider_op.update()

        # Subscreve ao sistema de temas para auto-atualização
        from ui.infrastructure.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self.on_theme_changed)
        self.on_theme_changed()

    def set_values(self, opacity, blend_mode, is_group=False):
        self.slider_op.blockSignals(True)
        self.combo_blend.blockSignals(True)
        try:
            val = int(opacity * 100 if isinstance(opacity, float) and opacity <= 1.0 else opacity)
            self.slider_op.setValue(val)

            pass_through_label = LayerBlendMode.PASS_THROUGH.label
            if is_group:
                if pass_through_label not in [self.combo_blend.itemText(i) for i in range(self.combo_blend.count())]:
                    self.combo_blend.insertItem(1, pass_through_label)
            else:
                idx = self.combo_blend.findText(pass_through_label)
                if idx >= 0:
                    self.combo_blend.removeItem(idx)

            # LayerBlendMode.coerce() aceita o enum, um int, o rotulo atual ou
            # qualquer variante legada de uma so vez -- ver
            # ui.core.document.layer_blend_mode para a lista completa; substitui
            # o legacy_map que so cobria 5 dessas variantes.
            clean_mode = LayerBlendMode.coerce(blend_mode).label
            idx = self.combo_blend.findText(clean_mode)
            if idx >= 0:
                self.combo_blend.setCurrentIndex(idx)
        finally:
            self.slider_op.blockSignals(False)
            self.combo_blend.blockSignals(False)

    def on_theme_changed(self, colors=None):
        """Aplica tema ao header. O argumento 'colors' é ignorado — lemos
        diretamente do ThemeManager para garantir consistência."""
        from ui.infrastructure.theme.manager import ThemeManager
        tm = ThemeManager.instance()
        bg_input    = tm.get_color("bg_panel", "#1f2937")
        border      = tm.get_color("border",   "#374151")
        accent      = tm.get_color("accent",   "#3b82f6")
        text_primary = tm.get_color("text_main", "#f3f4f6")
        fg_on_accent = tm.get_color("FG_PRIMARY", "#ffffff")

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
                selection-color: {fg_on_accent};
                border: 1px solid {border};
                outline: none;
            }}
        """
        self.combo_blend.setStyleSheet(sheet)

