from PySide6 import QtWidgets, QtCore, QtGui

class ColorButton(QtWidgets.QPushButton):
    colorChanged = QtCore.Signal(QtGui.QColor)

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor(color)
        self.setFixedSize(32, 32)
        self.clicked.connect(self.on_clicked)
        
        # Track theme changes
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._on_theme_changed)
        self.update_style()

    def update_style(self):
        from ui.core.theme.manager import ThemeManager
        border_color = ThemeManager.instance().get_color("border")
        self.setStyleSheet(f"background-color: {self.color.name()}; border: 2px solid {border_color}; border-radius: 6px;")

    def set_color(self, color):
        self.color = QtGui.QColor(color)
        self.update_style()

    def _on_theme_changed(self, theme_name):
        self.update_style()

    def on_clicked(self):
        color_dialog = QtWidgets.QColorDialog(self.color, self)
        if color_dialog.exec() == QtWidgets.QDialog.Accepted:
            self.set_color(color_dialog.selectedColor())
            self.colorChanged.emit(self.color)

class ColorPaletteGrid(QtWidgets.QWidget):
    colorSelected = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 10 harmonious curated colors matching Web UI palettes
        colors = [
            "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
            "#ffffff", "#9ca3af", "#4b5563", "#1f2937", "#000000"
        ]

        self.buttons = []
        for idx, color_hex in enumerate(colors):
            row = idx // 5
            col = idx % 5
            btn = QtWidgets.QPushButton(self)
            btn.setFixedSize(24, 24)
            btn.clicked.connect(lambda checked=False, c=color_hex: self.colorSelected.emit(QtGui.QColor(c)))
            layout.addWidget(btn, row, col)
            self.buttons.append((btn, color_hex))
            
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self.update_styles)
        self.update_styles()

    def update_styles(self):
        from ui.core.theme.manager import ThemeManager
        border_color = ThemeManager.instance().get_color("border")
        for btn, color_hex in self.buttons:
            btn.setStyleSheet(f"background-color: {color_hex}; border: 1px solid {border_color}; border-radius: 4px;")
