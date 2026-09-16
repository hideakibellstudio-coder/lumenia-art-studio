from PySide6 import QtWidgets, QtCore, QtGui

class ToggleSwitch(QtWidgets.QAbstractButton):
    def __init__(self, parent=None, active_color=None, bg_color=None, thumb_color=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self._margin = 3
        self._thumb_width = 18
        
        # Fallbacks iniciais
        self._active_color = QtGui.QColor("#6366f1")
        self._bg_color = QtGui.QColor("#2e2e38")
        self._thumb_color = QtGui.QColor("#ffffff")
        self._disabled_color = QtGui.QColor("#1e1e24")
        
        self.update_theme_colors()
        
        # Se cores explícitas foram informadas, as respeitamos
        if active_color: self._active_color = QtGui.QColor(active_color)
        if bg_color: self._bg_color = QtGui.QColor(bg_color)
        if thumb_color: self._thumb_color = QtGui.QColor(thumb_color)
        
        # Conecta à troca de tema
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self.update_theme_colors)
        
        # Animation
        self._thumb_position = self._get_start_position()
        self.anim = QtCore.QPropertyAnimation(self, b"thumb_position", self)
        self.anim.setDuration(120)
        self.anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

    def _get_start_position(self) -> float:
        return float(self._margin)

    def _get_end_position(self) -> float:
        w = self.width() if self.width() > 0 else self.sizeHint().width()
        return float(w - self._thumb_width - self._margin)

    def update_theme_colors(self):
        from ui.core.theme.manager import ThemeManager
        theme = ThemeManager.instance()._themes.get(ThemeManager.instance().current_theme, {})
        colors = theme.get("colors", {})
        
        self._active_color = QtGui.QColor(ThemeManager.instance().resolve_color("ACCENT", colors))
        self._bg_color = QtGui.QColor(ThemeManager.instance().resolve_color("BORDER", colors))
        self._thumb_color = QtGui.QColor(ThemeManager.instance().resolve_color("text_main", colors))
        self._disabled_color = QtGui.QColor(ThemeManager.instance().resolve_color("BG_DARKER", colors))
        self.update()

    @QtCore.Property(float)
    def thumb_position(self) -> float:
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos: float):
        self._thumb_position = pos
        self.update()

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(46, 24)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        r = self.rect()
        bg_path = QtGui.QPainterPath()
        bg_path.addRoundedRect(r.x(), r.y(), r.width(), r.height(), r.height() / 2, r.height() / 2)
        
        if not self.isEnabled():
            bg_color = self._disabled_color
        elif self.isChecked():
            bg_color = self._active_color
        else:
            bg_color = self._bg_color
            
        p.fillPath(bg_path, bg_color)
        
        # Se não estiver em animação, garante o thumb na posição exata de start ou end
        if self.anim.state() != QtCore.QAbstractAnimation.Running:
            self._thumb_position = self._get_end_position() if self.isChecked() else self._get_start_position()

        thumb_y = self._margin
        thumb_h = r.height() - (2 * self._margin)
        p.setBrush(self._thumb_color)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(self._thumb_position, thumb_y, self._thumb_width, thumb_h)
        p.end()

    def nextCheckState(self):
        super().nextCheckState()
        self._animate(self.isChecked())

    def _animate(self, checked: bool):
        start = self._get_start_position()
        end = self._get_end_position()
        self.anim.stop()
        self.anim.setStartValue(self._thumb_position)
        self.anim.setEndValue(end if checked else start)
        self.anim.start()

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._thumb_position = self._get_end_position() if checked else self._get_start_position()
        self.update()
