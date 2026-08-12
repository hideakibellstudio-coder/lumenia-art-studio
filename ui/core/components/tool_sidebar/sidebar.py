from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon

class ToolSidebar(QtWidgets.QToolBar):
    brushSelected = QtCore.Signal()
    eraserSelected = QtCore.Signal()
    zoomInRequested = QtCore.Signal()
    zoomOutRequested = QtCore.Signal()
    resetRequested = QtCore.Signal()
    clearRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Ferramentas", parent)
        self.setMovable(False)
        self.setOrientation(QtCore.Qt.Horizontal)
        self.setIconSize(QtCore.QSize(20, 20))
        
        self.setup_actions()
        
        # Track theme changes to keep icons colorized
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._on_theme_changed)

    def setup_actions(self):
        self.clear()
        
        # Pincel
        self.action_brush = QtGui.QAction(get_icon("brush"), "Pincel", self)
        self.action_brush.setCheckable(True)
        self.action_brush.setChecked(True)
        self.action_brush.triggered.connect(self._on_brush_triggered)
        self.addAction(self.action_brush)
        
        # Borracha
        self.action_eraser = QtGui.QAction(get_icon("eraser"), "Borracha", self)
        self.action_eraser.setCheckable(True)
        self.action_eraser.triggered.connect(self._on_eraser_triggered)
        self.addAction(self.action_eraser)
        
        self.addSeparator()
        
        # Zoom In
        action_zoom_in = QtGui.QAction(get_icon("zoom_in"), "Aproximar (Zoom In)", self)
        action_zoom_in.triggered.connect(self.zoomInRequested.emit)
        self.addAction(action_zoom_in)
        
        # Zoom Out
        action_zoom_out = QtGui.QAction(get_icon("zoom_out"), "Afastar (Zoom Out)", self)
        action_zoom_out.triggered.connect(self.zoomOutRequested.emit)
        self.addAction(action_zoom_out)

        self.addSeparator()

        # Reset
        action_reset = QtGui.QAction(get_icon("reset"), "Resetar Visão", self)
        action_reset.triggered.connect(self.resetRequested.emit)
        self.addAction(action_reset)

        self.addSeparator()

        # Limpar Tela
        action_clear = QtGui.QAction(get_icon("trash"), "Limpar Tela", self)
        action_clear.triggered.connect(self.clearRequested.emit)
        self.addAction(action_clear)

    def _on_brush_triggered(self):
        self.action_brush.setChecked(True)
        self.action_eraser.setChecked(False)
        self.brushSelected.emit()

    def _on_eraser_triggered(self):
        self.action_brush.setChecked(False)
        self.action_eraser.setChecked(True)
        self.eraserSelected.emit()



    def _on_theme_changed(self, theme_name: str):
        # Update all action icons with new theme color
        brush_checked = self.action_brush.isChecked()
        eraser_checked = self.action_eraser.isChecked()
        
        self.setup_actions()
        
        self.action_brush.setChecked(brush_checked)
        self.action_eraser.setChecked(eraser_checked)
