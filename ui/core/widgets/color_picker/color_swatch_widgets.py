"""Color swatch and auxiliary widgets for ColorWheel."""

from PySide6 import QtWidgets, QtCore, QtGui


class IconButton(QtWidgets.QToolButton):
    def __init__(self, icon_name, tooltip="", parent=None, size=28, icon_size=18, checkable=False, icon_color=None):
        super().__init__(parent)
        self.setProperty("icon_name", icon_name)
        if icon_name:
            from ui.core.icons import get_icon
            self.setIcon(get_icon(icon_name, icon_color))
            
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setAutoRaise(True)
        if checkable: 
            self.setCheckable(True)


class OverlappingColorSwitcher(QtWidgets.QWidget):
    primaryChanged = QtCore.Signal(QtGui.QColor)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(50, 50) 
        
        self.fg_color = QtGui.QColor("#3b82f6")
        self.bg_color = QtGui.QColor("#ffffff")
        self.check_pix = self._create_checkerboard(8)

    def _create_checkerboard(self, size):
        pix = QtGui.QPixmap(size, size)
        pix.fill(QtCore.Qt.white)
        p = QtGui.QPainter(pix)
        c = QtGui.QColor(200, 200, 200)
        half = size // 2
        p.fillRect(0, 0, half, half, c)
        p.fillRect(half, half, half, half, c)
        p.end()
        return pix

    def set_primary(self, color):
        self.fg_color = color
        self.update()

    def set_secondary(self, color):
        self.bg_color = color
        self.update()

    def swap_colors(self):
        self.fg_color, self.bg_color = self.bg_color, self.fg_color
        self.update()
        self.primaryChanged.emit(self.fg_color)

    def set_transparent(self):
        self.fg_color = QtGui.QColor(0, 0, 0, 0)
        self.update()
        self.primaryChanged.emit(self.fg_color)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, False) 
        
        w, h = self.width(), self.height()
        swatch_size = 34
        
        bg_rect = QtCore.QRect(w - swatch_size, h - swatch_size, swatch_size, swatch_size)
        self._draw_swatch(p, bg_rect, self.bg_color)
        self._bg_hit_rect = bg_rect

        fg_rect = QtCore.QRect(0, 0, swatch_size, swatch_size)
        self._draw_swatch(p, fg_rect, self.fg_color)
        self._fg_hit_rect = fg_rect

    def _draw_swatch(self, painter, rect, color):
        painter.save()
        if color.alpha() < 255:
            painter.setBrush(QtGui.QBrush(self.check_pix))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(rect)
        
        painter.setBrush(color)
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 60), 1))
        painter.drawRect(rect)
        
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 50), 1))
        painter.drawRect(rect.adjusted(1, 1, -1, -1))
        
        painter.restore()

    def mousePressEvent(self, event):
        pos = event.pos()
        if hasattr(self, '_fg_hit_rect') and self._fg_hit_rect.contains(pos):
            self.primaryChanged.emit(self.fg_color)
            return
        if hasattr(self, '_bg_hit_rect') and self._bg_hit_rect.contains(pos):
            self.swap_colors()
            return


class TransparencyButton(QtWidgets.QWidget):
    clicked = QtCore.Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(18, 18) 
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.check_pix = self._create_checkerboard(4)

    def _create_checkerboard(self, size):
        pix = QtGui.QPixmap(size, size)
        pix.fill(QtCore.Qt.white)
        p = QtGui.QPainter(pix)
        c = QtGui.QColor(200, 200, 200)
        half = size // 2
        p.fillRect(0, 0, half, half, c)
        p.fillRect(half, half, half, half, c)
        p.end()
        return pix

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        p.setBrush(QtGui.QBrush(self.check_pix))
        p.setPen(QtGui.QPen(QtGui.QColor(100, 100, 100), 1))
        p.drawRect(rect)
        p.setPen(QtGui.QPen(QtGui.QColor(200, 50, 50), 2))
        p.drawLine(rect.bottomLeft(), rect.topRight())

    def mousePressEvent(self, event):
        self.clicked.emit()


class HexWidget(QtWidgets.QWidget):
    colorChanged = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.input = QtWidgets.QLineEdit("#000000")
        self.input.setMaxLength(7)
        self.input.setFixedHeight(22)
        self.input.setObjectName("hexInput")
        self.input.editingFinished.connect(self._parse_input)
        
        self.btn_copy = IconButton("copy", "Copiar Hex")
        self.btn_copy.setFixedSize(22, 22)
        self.btn_copy.setIconSize(QtCore.QSize(14, 14))
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        
        layout.addWidget(self.input)
        layout.addWidget(self.btn_copy)

    def update_theme(self):
        from ui.core.theme.manager import ThemeManager
        fg = ThemeManager.instance().get_color("text_main")
        from ui.core.icons import get_icon
        self.btn_copy.setIcon(get_icon("copy", fg))

    def set_color(self, color):
        self.input.setText(color.name().upper())

    def _parse_input(self):
        text = self.input.text()
        if not text.startswith("#"):
            text = "#" + text
        
        color = QtGui.QColor(text)
        if color.isValid():
            self.colorChanged.emit(color)

    def _copy_to_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.input.text())


class RecentColorsWidget(QtWidgets.QFrame):
    colorSelected = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent=None, max_colors=10):
        super().__init__(parent)
        self.setObjectName("RecentColors")
        self.max_colors = max_colors
        self._colors = []
        self._buttons = []
        
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        
        for i in range(self.max_colors):
            btn = QtWidgets.QPushButton()
            btn.setFixedSize(18, 18)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 1px solid #333;
                    border-radius: 6px;
                    padding: 0px;
                    margin: 0px;
                }
            """)
            btn.clicked.connect(lambda checked=False, idx=i: self._on_button_clicked(idx))
            self._buttons.append(btn)
            layout.addWidget(btn, i // 5, i % 5)
            
    def update_theme(self):
        from ui.core.theme.manager import ThemeManager
        border = ThemeManager.instance().get_color("border")
        self.setStyleSheet(f"""
            QFrame#RecentColors {{
                background-color: transparent;
                border: 1px solid {border};
                border-radius: 4px;
            }}
        """)
        self._update_buttons(border)
            
    def add_color(self, color: QtGui.QColor, source=None):
        if not color.isValid() or color.alpha() == 0:
            return
            
        hex_val = color.name().upper()
        if self._colors and self._colors[0].name().upper() == hex_val:
            return
            
        if source == "mixer" and self._colors:
            self._colors[0] = color
        else:
            self._colors.insert(0, color)
            if len(self._colors) > self.max_colors:
                self._colors.pop()
            
        self._update_buttons()
        
    def _update_buttons(self, border_color=None):
        from ui.core.theme.manager import ThemeManager
        if border_color is None:
            border_color = ThemeManager.instance().get_color("border")
        hover_color = ThemeManager.instance().get_color("FG_PRIMARY", "#ffffff")
            
        for i, btn in enumerate(self._buttons):
            if i < len(self._colors):
                c = self._colors[i].name()
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {c};
                        border: 1px solid {border_color};
                        border-radius: 6px;
                        padding: 0px;
                        margin: 0px;
                    }}
                    QPushButton:hover {{
                        border: 1px solid {hover_color};
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: 1px dashed {border_color};
                        border-radius: 6px;
                        padding: 0px;
                        margin: 0px;
                    }}
                """)

    def _on_button_clicked(self, idx):
        if idx < len(self._colors):
            self.colorSelected.emit(self._colors[idx])
