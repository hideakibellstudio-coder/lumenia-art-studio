from PySide6 import QtWidgets, QtCore, QtGui
import math
import os

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
        if self._fg_hit_rect.contains(pos):
            self.primaryChanged.emit(self.fg_color)
            return
        if self._bg_hit_rect.contains(pos):
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
        if border_color is None:
            from ui.core.theme.manager import ThemeManager
            border_color = ThemeManager.instance().get_color("border")
            
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
                        border: 1px solid #ffffff;
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


class WheelArea(QtWidgets.QWidget):
    colorChanged = QtCore.Signal(QtGui.QColor)
    colorCommitted = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._h, self._s, self._v = 0.0, 1.0, 1.0
        self._wheel_pixmap = None
        self._last_size = QtCore.QSize()
        self._dragging_part = None
        self.wheel_thickness = 20
        self.setMouseTracking(True)

    def get_current_color(self) -> QtGui.QColor:
        return QtGui.QColor.fromHsvF(self._h, self._s, self._v, 1.0)

    def set_color(self, color: QtGui.QColor):
        if not color.isValid(): 
            return
        h, s, v, a = color.getHsvF()
        if h < 0: 
            h = self._h 
        if (abs(h - self._h) > 1e-5 or abs(s - self._s) > 1e-5 or abs(v - self._v) > 1e-5):
            self._h, self._s, self._v = h, s, v
            self.update()

    def _update_from_pos(self, pos: QtCore.QPoint):
        center = QtCore.QPoint(self.width() // 2, self.height() // 2)
        radius = min(self.width(), self.height()) / 2.0
        
        if self._dragging_part == 'square':
            square_radius = (radius - self.wheel_thickness - 6) / math.sqrt(2)
            square_top_left = center - QtCore.QPoint(int(square_radius), int(square_radius))
            x = max(0.0, min(float(pos.x() - square_top_left.x()), square_radius * 2))
            y = max(0.0, min(float(pos.y() - square_top_left.y()), square_radius * 2))
            self._s = x / (square_radius * 2)
            self._v = 1.0 - (y / (square_radius * 2))
            
        elif self._dragging_part == 'wheel':
            dx = pos.x() - center.x()
            dy = -(pos.y() - center.y())
            angle = math.atan2(dy, dx)
            if angle < 0: 
                angle += 2 * math.pi
            self._h = angle / (2 * math.pi)

        self.update()
        self.colorChanged.emit(self.get_current_color())

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            center = QtCore.QPoint(self.width() // 2, self.height() // 2)
            radius = min(self.width(), self.height()) / 2.0
            inner_radius = radius - self.wheel_thickness
            dist = math.hypot(event.x() - center.x(), event.y() - center.y())
            
            if inner_radius <= dist <= radius:
                self._dragging_part = 'wheel'
            elif dist < inner_radius:
                self._dragging_part = 'square'
            else:
                self._dragging_part = None
            if self._dragging_part:
                self._update_from_pos(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton and self._dragging_part:
            self._update_from_pos(event.pos())

    def mouseReleaseEvent(self, event):
        if self._dragging_part:
            self.colorCommitted.emit(self.get_current_color())
        self._dragging_part = None
        
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        if self.size() != self._last_size:
            self._wheel_pixmap = None
            self._last_size = self.size()
        self._draw_hue_wheel(painter)
        self._draw_sv_square(painter)
        self._draw_markers(painter)

    def _draw_hue_wheel(self, painter):
        center = QtCore.QPoint(self.width() // 2, self.height() // 2)
        radius = int(min(self.width(), self.height()) / 2.0) - 2
        if radius <= 0:
            return
        if self._wheel_pixmap is None:
            self._wheel_pixmap = QtGui.QPixmap(self.size())
            self._wheel_pixmap.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(self._wheel_pixmap)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            gradient = QtGui.QConicalGradient(center, 0)
            for i in range(361):
                hue = i / 360.0
                gradient.setColorAt(hue, QtGui.QColor.fromHsvF(hue, 1.0, 1.0, 1.0))
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QBrush(gradient))
            p.drawEllipse(center, radius, radius)
            inner_radius = radius - self.wheel_thickness
            p.setBrush(QtGui.QColor(0, 0, 0, 0))
            p.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            p.drawEllipse(center, inner_radius, inner_radius)
            p.end()
        painter.drawPixmap(0, 0, self._wheel_pixmap)

    def _draw_sv_square(self, painter):
        center = QtCore.QPoint(self.width() // 2, self.height() // 2)
        radius = min(self.width(), self.height()) / 2.0 - 2
        square_radius = int((radius - self.wheel_thickness - 6) / math.sqrt(2))
        if square_radius <= 0:
            return
        rect = QtCore.QRect(center.x() - square_radius, center.y() - square_radius, 
                     2 * square_radius, 2 * square_radius)
        sat_gradient = QtGui.QLinearGradient(rect.topLeft(), rect.topRight())
        sat_gradient.setColorAt(0, QtGui.QColor.fromHsvF(self._h, 0.0, 1.0, 1.0))
        sat_gradient.setColorAt(1, QtGui.QColor.fromHsvF(self._h, 1.0, 1.0, 1.0))
        painter.fillRect(rect, sat_gradient)
        val_gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
        val_gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
        val_gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 255))
        painter.fillRect(rect, val_gradient)

    def _draw_markers(self, painter):
        center = QtCore.QPoint(self.width() // 2, self.height() // 2)
        radius = min(self.width(), self.height()) / 2.0 - 2
        marker_radius_pos = radius - self.wheel_thickness / 2
        angle = self._h * 2 * math.pi
        hue_x = int(marker_radius_pos * math.cos(angle))
        hue_y = int(-marker_radius_pos * math.sin(angle))
        
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        painter.setBrush(QtCore.Qt.white)
        painter.drawEllipse(center + QtCore.QPoint(hue_x, hue_y), 5, 5)

        square_radius = (radius - self.wheel_thickness - 6) / math.sqrt(2)
        if square_radius <= 0:
            return
        square_top_left = center - QtCore.QPoint(int(square_radius), int(square_radius))
        square_marker_x = int(self._s * square_radius * 2)
        square_marker_y = int((1.0 - self._v) * square_radius * 2)
        pos = square_top_left + QtCore.QPoint(square_marker_x, square_marker_y)
        
        painter.setPen(QtGui.QPen(QtCore.Qt.black, 2))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawEllipse(pos, 6, 6)
        painter.setPen(QtGui.QPen(QtCore.Qt.white, 2))
        painter.drawEllipse(pos, 4, 4)


class ColorWheelWidget(QtWidgets.QWidget):
    colorChanged = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent=None, initial_color: QtGui.QColor = None):
        super().__init__(parent)
        self._initial_color = initial_color or QtGui.QColor("#3b82f6")
        self._updating_from_external = False
        
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.setMinimumHeight(300)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # 1. HEX HEADER
        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        
        self.hex_widget = HexWidget()
        self.hex_widget.colorChanged.connect(self._on_manual_input)
        header.addWidget(self.hex_widget, alignment=QtCore.Qt.AlignCenter)
        
        main_layout.addLayout(header)

        # 2. COLOR WHEEL AREA
        self.wheel = WheelArea()
        self.wheel.colorChanged.connect(self._on_wheel_changed)
        self.wheel.colorCommitted.connect(self._on_color_committed)
        self.wheel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        main_layout.addWidget(self.wheel, 1)

        # 3. CENTRAL SECTION (Recent Colors + Switcher)
        mid_layout = QtWidgets.QHBoxLayout()
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(10)
        
        # Recent Colors (Left)
        recent_container = QtWidgets.QWidget()
        recent_vbox = QtWidgets.QVBoxLayout(recent_container)
        recent_vbox.setContentsMargins(0, 0, 0, 0)
        recent_vbox.setSpacing(4)
        
        lbl_recent = QtWidgets.QLabel("CORES RECENTES")
        lbl_recent.setStyleSheet("font-size: 10px; font-weight: bold; color: #8b949e;")

        
        self.recent_colors = RecentColorsWidget()
        self.recent_colors.colorSelected.connect(self._on_manual_input)
        
        recent_vbox.addWidget(lbl_recent)
        recent_vbox.addWidget(self.recent_colors)
        mid_layout.addWidget(recent_container, 1)
        
        # Vertical Separator Line
        self.vline = QtWidgets.QFrame()
        self.vline.setFrameShape(QtWidgets.QFrame.VLine)
        self.vline.setObjectName("ColorWheelVLine")
        mid_layout.addWidget(self.vline)
        
        # Color Switcher Host (Right)
        switcher_host = QtWidgets.QWidget()
        switcher_host.setFixedSize(72, 72)
        switcher_host.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.switcher = OverlappingColorSwitcher(switcher_host)
        self.switcher.primaryChanged.connect(self._on_switcher_changed)
        self.switcher.move(12, 12)
        
        self.btn_swap = IconButton("arrow-swap", "Trocar cores", switcher_host, size=18, icon_size=12)
        self.btn_swap.move(54, 0)
        self.btn_swap.clicked.connect(self._swap_clicked)

        self.btn_trans = TransparencyButton(switcher_host)
        self.btn_trans.move(0, 54)
        self.btn_trans.clicked.connect(self.switcher.set_transparent)
        
        mid_layout.addWidget(switcher_host)
        main_layout.addLayout(mid_layout)

        # Initial Color — matches whatever the app passes in (or #3b82f6 default)
        start_color = self._initial_color
        self.set_color(start_color)
        
        # Connect to theme manager
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._on_theme_changed)
        self.update_theme_styles()

    def _on_theme_changed(self, theme_name: str):
        self.update_theme_styles()

    def update_theme_styles(self):
        from ui.core.theme.manager import ThemeManager
        fg_primary = ThemeManager.instance().get_color("text_main")
        border = ThemeManager.instance().get_color("border")
        
        self.hex_widget.update_theme()
        self.recent_colors.update_theme()
        
        from ui.core.icons import get_icon
        self.btn_swap.setIcon(get_icon("arrow-swap", fg_primary))
        self.vline.setStyleSheet(f"background-color: {border}; max-width: 1px;")

    def set_color(self, color: QtGui.QColor):
        if color.alpha() == 0:
            self.switcher.set_transparent()
        else:
            self.switcher.set_primary(color)
            self.wheel.set_color(color)
        self.hex_widget.set_color(color)

    def _on_wheel_changed(self, color: QtGui.QColor):
        if self._updating_from_external: 
            return
        self._updating_from_external = True
        self.switcher.set_primary(color)
        self.hex_widget.set_color(color)
        self.colorChanged.emit(color)
        self._updating_from_external = False

    def _on_switcher_changed(self, color: QtGui.QColor):
        if self._updating_from_external: 
            return
        self._updating_from_external = True
        if color.alpha() != 0:
            self.wheel.set_color(color)
        self.hex_widget.set_color(color)
        self.colorChanged.emit(color)
        self._updating_from_external = False

    def _on_manual_input(self, color: QtGui.QColor):
        if self._updating_from_external: 
            return
        self._updating_from_external = True
        self.set_color(color)
        self.colorChanged.emit(color)
        self._updating_from_external = False

    def _swap_clicked(self):
        self.switcher.swap_colors()
        c = self.switcher.fg_color
        
        if self._updating_from_external: 
            return
        self._updating_from_external = True
        if c.alpha() != 0:
            self.wheel.set_color(c)
        self.hex_widget.set_color(c)
        self.colorChanged.emit(c)
        self._updating_from_external = False

    def _on_color_committed(self, color: QtGui.QColor):
        self.recent_colors.add_color(color)
