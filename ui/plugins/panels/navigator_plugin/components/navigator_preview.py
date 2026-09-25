from PySide6 import QtWidgets, QtCore, QtGui
import math

class IconButton(QtWidgets.QToolButton):
    def __init__(self, icon_name, tooltip="", parent=None, size=28, icon_size=18, checkable=False, icon_color=None):
        super().__init__(parent)
        self.setProperty("icon_name", icon_name)
        if icon_name:
            from ui.infrastructure.icons import get_icon
            self.setIcon(get_icon(icon_name, icon_color))
            
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self.setIconSize(QtCore.QSize(icon_size, icon_size))
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setAutoRaise(True)
        if checkable: 
            self.setCheckable(True)


class NavigatorPreview(QtWidgets.QWidget):
    panRequested = QtCore.Signal(float, float)
    zoomRequested = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setStyleSheet("NavigatorPreview { background-color: transparent; }")
        
        # Default design colors
        self._color_paper = QtGui.QColor("#ffffff")
        self._color_border = QtGui.QColor("#334155")
        self._color_accent = QtGui.QColor("#3b82f6")
        self._color_canvas_bg = QtGui.QColor("#e2e8f0")
        self._color_empty_bg = QtGui.QColor("#262626")
        
        self.zoom_level = 1.0 
        self.cam_x = 0.5 
        self.cam_y = 0.5
        self.rotation = 0.0
        self.flip_x = False
        self.flip_y = False
        self.ratio_w = 1.0
        self.ratio_h = 1.0
        self.aspect_ratio = 1920.0 / 1080.0
        
        self.has_document = False
        self.artwork_pix = None
        self._is_dragging = False
        self._drag_offset = QtCore.QPointF(0, 0)
        
        self.update_theme()
        from ui.infrastructure.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self.update_theme)

    def update_theme(self, theme_name=None):
        from ui.infrastructure.theme.manager import ThemeManager
        theme = ThemeManager.instance()._themes.get(ThemeManager.instance().current_theme, {})
        colors = theme.get("colors", {})
        
        self._color_border = QtGui.QColor(ThemeManager.instance().resolve_color("BORDER", colors))
        self._color_accent = QtGui.QColor(ThemeManager.instance().resolve_color("ACCENT", colors))
        self._color_canvas_bg = QtGui.QColor(ThemeManager.instance().resolve_color("BG_LIGHT", colors))
        self._color_empty_bg = QtGui.QColor(ThemeManager.instance().resolve_color("bg_panel", colors))
        self.update()

    def set_canvas_size(self, width: int, height: int) -> None:
        if width > 0 and height > 0:
            self.aspect_ratio = float(width) / float(height)
            self.update()

    def set_artwork(self, pix):
        if isinstance(pix, QtGui.QImage):
            if pix.width() > 0 and pix.height() > 0:
                self.aspect_ratio = float(pix.width()) / float(pix.height())
            self.artwork_pix = QtGui.QPixmap.fromImage(pix)
        elif isinstance(pix, QtGui.QPixmap):
            if pix.width() > 0 and pix.height() > 0:
                self.aspect_ratio = float(pix.width()) / float(pix.height())
            self.artwork_pix = pix
        else:
            self.artwork_pix = None
        self.update()

    def update_state(self, zoom, x, y, rotation, flip_x, flip_y, ratio_w=1.0, ratio_h=1.0):
        self.zoom_level = zoom
        self.cam_x = x
        self.cam_y = y
        self.rotation = rotation
        self.flip_x = flip_x
        self.flip_y = flip_y
        self.ratio_w = ratio_w
        self.ratio_h = ratio_h
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        if not self.has_document:
            p.setBrush(self._color_empty_bg)
            p.setPen(QtCore.Qt.NoPen)
            p.drawRect(self.rect())
            p.end()
            return
            
        rect = self.rect()
        margin = 10
        avail_w = rect.width() - margin * 2
        avail_h = rect.height() - margin * 2
        
        if avail_w <= 0 or avail_h <= 0:
            p.end()
            return
            
        draw_w = avail_w
        draw_h = draw_w / self.aspect_ratio
        
        if draw_h > avail_h:
            draw_h = avail_h
            draw_w = draw_h * self.aspect_ratio
            
        ox = margin + (avail_w - draw_w) / 2
        oy = margin + (avail_h - draw_h) / 2
        
        self.draw_rect = QtCore.QRectF(ox, oy, draw_w, draw_h)
        
        # Draw Thumbnail Base (Paper)
        p.setBrush(self._color_paper)
        p.setPen(QtGui.QPen(self._color_border, 1))
        p.drawRect(self.draw_rect)
        
        # Draw Real Artwork Pixmap or Checkerboard Fallback
        if self.artwork_pix and not self.artwork_pix.isNull():
            p.drawPixmap(self.draw_rect.toRect(), self.artwork_pix)
        else:
            p.setBrush(self._color_canvas_bg)
            p.setPen(QtCore.Qt.NoPen)
            p.drawRect(self.draw_rect.adjusted(2, 2, -2, -2))
        
        # --- VIEWPORT RECTANGLE ---
        if self.has_document:
            vw = draw_w * self.ratio_w
            vh = draw_h * self.ratio_h
            
            tx = ox + self.cam_x * draw_w
            ty = oy + self.cam_y * draw_h
            
            p.save()
            p.translate(tx, ty)
            p.rotate(-self.rotation)
            
            sx = -1 if self.flip_x else 1
            sy = -1 if self.flip_y else 1
            p.scale(sx, sy)
            
            viewport_rect = QtCore.QRectF(-vw/2, -vh/2, vw, vh)
            self.viewport_rect = viewport_rect
            
            p.setPen(QtGui.QPen(self._color_accent, 2))
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawRect(viewport_rect)
            
            # Crosshair center
            p.setPen(QtGui.QPen(self._color_accent, 1, QtCore.Qt.DotLine))
            p.drawLine(QtCore.QPointF(-10, 0), QtCore.QPointF(10, 0))
            p.drawLine(QtCore.QPointF(0, -10), QtCore.QPointF(0, 10))
            
            p.restore()
        
        p.end()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.zoomRequested.emit(delta)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            local_pos = event.position()
            if hasattr(self, 'draw_rect'):
                tx = self.draw_rect.x() + self.cam_x * self.draw_rect.width()
                ty = self.draw_rect.y() + self.cam_y * self.draw_rect.height()
                viewport_center = QtCore.QPointF(tx, ty)
                
                vw = self.draw_rect.width() * self.ratio_w
                vh = self.draw_rect.height() * self.ratio_h
                local_viewport_rect = QtCore.QRectF(tx - vw/2, ty - vh/2, vw, vh)
                
                if local_viewport_rect.contains(local_pos):
                    self._is_dragging = True
                    self._drag_offset = viewport_center - local_pos
                else:
                    self._is_dragging = True
                    self._drag_offset = QtCore.QPointF(0, 0)
                    self._handle_input(event.position())

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self._handle_input(event.position() + self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._is_dragging = False

    def _handle_input(self, local_pos):
        if not hasattr(self, 'draw_rect'): 
            return
        
        rel_x = local_pos.x() - self.draw_rect.x()
        rel_y = local_pos.y() - self.draw_rect.y()
        
        norm_x = max(0.0, min(1.0, rel_x / self.draw_rect.width()))
        norm_y = max(0.0, min(1.0, rel_y / self.draw_rect.height()))
        
        self.panRequested.emit(norm_x, norm_y)
