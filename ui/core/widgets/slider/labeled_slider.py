from PySide6 import QtWidgets, QtCore

class NonScrollSlider(QtWidgets.QSlider):
    def wheelEvent(self, event):
        # Ignore the event so it propagates up to the QScrollArea
        event.ignore()

class LabeledSlider(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(float)
    pinToggled   = QtCore.Signal(str, bool)

    def __init__(self, label_text: str, min_val: int, max_val: int, default_val: int,
                 value_suffix: str = "", divisor: float = 1.0, parent=None,
                 param_name: str = "", show_pin: bool = False, default_pinned: bool = False):
        super().__init__(parent)
        self.divisor = divisor
        self.suffix = value_suffix
        self.param_name = param_name
        self.show_pin = show_pin
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Header row
        header_layout = QtWidgets.QHBoxLayout()
        self.lbl_title = QtWidgets.QLabel(label_text)
        
        # ThemeManager accent color colorized label
        from ui.core.theme.manager import ThemeManager
        accent_color = ThemeManager.instance().get_color("accent")
        
        self.lbl_val = QtWidgets.QLabel(self._format_value(default_val / divisor))
        self.lbl_val.setStyleSheet(f"font-weight: bold; color: {accent_color};")
        
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_val)

        if self.show_pin and self.param_name:
            self.pin_cb = QtWidgets.QCheckBox(self)
            self.pin_cb.setToolTip("Fixar no painel rápido")
            self.pin_cb.setFixedWidth(18)
            self.pin_cb.setCursor(QtCore.Qt.PointingHandCursor)
            self.pin_cb.setChecked(default_pinned)
            self.pin_cb.stateChanged.connect(lambda state: self.pinToggled.emit(self.param_name, self.pin_cb.isChecked()))
            header_layout.addWidget(self.pin_cb)

        layout.addLayout(header_layout)
        
        # Slider
        self.slider = NonScrollSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default_val)
        self.slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.slider)
        
        # Connect to theme changes to keep text accent updated
        ThemeManager.instance().themeChanged.connect(self._on_theme_changed)
        
    def _format_value(self, val: float) -> str:
        if self.divisor == 1.0:
            return f"{int(val)}{self.suffix}"
        else:
            return f"{val:.2f}{self.suffix}"
            
    def _on_value_changed(self, val: int):
        actual_val = val / self.divisor
        self.lbl_val.setText(self._format_value(actual_val))
        self.valueChanged.emit(actual_val)
        
    def _on_theme_changed(self, theme_name: str):
        from ui.core.theme.manager import ThemeManager
        accent_color = ThemeManager.instance().get_color("accent")
        self.lbl_val.setStyleSheet(f"font-weight: bold; color: {accent_color};")
        
    def value(self) -> float:
        return self.slider.value() / self.divisor
        
    def setValue(self, val: float):
        self.slider.setValue(int(val * self.divisor))
        
    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        self.slider.setEnabled(enabled)
