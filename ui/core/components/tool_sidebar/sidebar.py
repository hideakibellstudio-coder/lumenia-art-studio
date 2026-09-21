"""
ToolSidebar — Barra Superior de Ferramentas Rápidas (ARCcC i18n).
=================================================================
Fornece acesso rápido às ferramentas de pincel, borracha, formas, histórico e zoom.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon
from ui.core.i18n import tr, I18nManager


class ToolSidebar(QtWidgets.QToolBar):
    brushSelected = QtCore.Signal()
    eraserSelected = QtCore.Signal()
    shapesSelected = QtCore.Signal()
    undoRequested = QtCore.Signal()
    redoRequested = QtCore.Signal()
    zoomInRequested = QtCore.Signal()
    zoomOutRequested = QtCore.Signal()
    resetRequested = QtCore.Signal()
    clearRequested = QtCore.Signal()
    deselectRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Ferramentas", parent)
        self.setMovable(False)
        self.setOrientation(QtCore.Qt.Horizontal)
        self.setIconSize(QtCore.QSize(20, 20))
        
        self.setup_actions()
        self.retranslate_ui()
        
        # Track theme changes to keep icons colorized
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._on_theme_changed)
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def setup_actions(self):
        self.clear()
        
        # Pincel
        self.action_brush = QtGui.QAction(get_icon("brush"), "", self)
        self.action_brush.setCheckable(True)
        self.action_brush.setChecked(True)
        self.action_brush.triggered.connect(self._on_brush_triggered)
        self.addAction(self.action_brush)
        
        # Borracha
        self.action_eraser = QtGui.QAction(get_icon("eraser"), "", self)
        self.action_eraser.setCheckable(True)
        self.action_eraser.triggered.connect(self._on_eraser_triggered)
        self.addAction(self.action_eraser)

        # Formas Vetoriais
        self.action_shapes = QtGui.QAction(get_icon("shapes"), "", self)
        self.action_shapes.setCheckable(True)
        self.action_shapes.triggered.connect(self._on_shapes_triggered)
        self.addAction(self.action_shapes)
        
        self.addSeparator()

        # Desfazer (Undo)
        self.action_undo = QtGui.QAction(get_icon("undo"), "", self)
        self.action_undo.triggered.connect(self.undoRequested.emit)
        self.addAction(self.action_undo)

        # Refazer (Redo)
        self.action_redo = QtGui.QAction(get_icon("redo"), "", self)
        self.action_redo.triggered.connect(self.redoRequested.emit)
        self.addAction(self.action_redo)

        self.addSeparator()
        
        # Zoom In
        self.action_zoom_in = QtGui.QAction(get_icon("zoom_in"), "", self)
        self.action_zoom_in.triggered.connect(self.zoomInRequested.emit)
        self.addAction(self.action_zoom_in)
        
        # Zoom Out
        self.action_zoom_out = QtGui.QAction(get_icon("zoom_out"), "", self)
        self.action_zoom_out.triggered.connect(self.zoomOutRequested.emit)
        self.addAction(self.action_zoom_out)

        self.addSeparator()

        # Reset
        self.action_reset = QtGui.QAction(get_icon("reset"), "", self)
        self.action_reset.triggered.connect(self.resetRequested.emit)
        self.addAction(self.action_reset)

        # Desmarcar Seleção
        self.action_deselect = QtGui.QAction(get_icon("deselect"), "", self)
        self.action_deselect.triggered.connect(self.deselectRequested.emit)
        self.addAction(self.action_deselect)

        self.addSeparator()

        # Limpar Tela (Ação Destrutiva Isolada)
        self.action_clear = QtGui.QAction(get_icon("clean_layer"), "", self)
        self.action_clear.triggered.connect(self.clearRequested.emit)
        self.addAction(self.action_clear)

    def retranslate_ui(self):
        self.setWindowTitle(tr("tools.toolbar_title", "Ferramentas"))
        self.action_brush.setText(tr("tools.brush", "Pincel (B)"))
        self.action_brush.setToolTip(tr("tools.brush_tooltip", "Ferramenta de Pincel (B)"))
        self.action_eraser.setText(tr("tools.eraser", "Borracha (E)"))
        self.action_eraser.setToolTip(tr("tools.eraser_tooltip", "Ferramenta de Borracha (E)"))
        self.action_shapes.setText(tr("tools.shapes", "Formas Vetoriais (U)"))
        self.action_shapes.setToolTip(tr("tools.shapes_tooltip", "Formas Geométricas (U)"))
        self.action_undo.setText(tr("tools.undo", "Desfazer (Ctrl+Z)"))
        self.action_undo.setToolTip(tr("tools.undo_tooltip", "Desfazer última ação (Ctrl+Z)"))
        self.action_redo.setText(tr("tools.redo", "Refazer (Ctrl+Y)"))
        self.action_redo.setToolTip(tr("tools.redo_tooltip", "Refazer ação desfeita (Ctrl+Y)"))
        self.action_zoom_in.setText(tr("tools.zoom_in", "Aproximar (Zoom In)"))
        self.action_zoom_out.setText(tr("tools.zoom_out", "Afastar (Zoom Out)"))
        self.action_reset.setText(tr("tools.reset", "Resetar Câmera"))
        self.action_deselect.setText(tr("tools.deselect", "Desmarcar Seleção (Ctrl+D)"))
        self.action_clear.setText(tr("tools.clean", "Limpar Camada Ativa"))
        self.action_clear.setToolTip(tr("tools.clean_tooltip", "Limpar o conteúdo da camada ativa"))

    def _on_brush_triggered(self):
        self.action_brush.setChecked(True)
        self.action_eraser.setChecked(False)
        self.action_shapes.setChecked(False)
        self.brushSelected.emit()

    def _on_eraser_triggered(self):
        self.action_brush.setChecked(False)
        self.action_eraser.setChecked(True)
        self.action_shapes.setChecked(False)
        self.eraserSelected.emit()

    def _on_shapes_triggered(self):
        self.action_brush.setChecked(False)
        self.action_eraser.setChecked(False)
        self.action_shapes.setChecked(True)
        self.shapesSelected.emit()

    def _on_theme_changed(self, theme_name: str):
        self.setup_actions()
        self.retranslate_ui()
