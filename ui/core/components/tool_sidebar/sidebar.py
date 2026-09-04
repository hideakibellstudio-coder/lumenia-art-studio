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

        self.addSeparator()

        # ── Dropdown de Estabilização no Topo (ao lado de Limpar Tela) ──
        self.btn_stab_icon = QtWidgets.QToolButton(self)
        self.btn_stab_icon.setIcon(get_icon("stabilizer", "FG_SECONDARY"))
        self.btn_stab_icon.setToolTip(tr("tools.stabilizer_tooltip", "Perfil de Estabilização de Traço"))
        self.btn_stab_icon.setStyleSheet("border: none; background: transparent;")
        self.btn_stab_icon.setFixedSize(22, 22)
        self.addWidget(self.btn_stab_icon)

        from ui.core.engine.stabilizer_hub import StabilizerHub
        hub = StabilizerHub.instance()

        self.combo_stabilizer = QtWidgets.QComboBox()
        self.combo_stabilizer.setObjectName("TopBarStabilizerCombo")
        self.combo_stabilizer.setFixedHeight(24)
        self.combo_stabilizer.setMinimumWidth(180)
        self.combo_stabilizer.setToolTip(tr("tools.stabilizer_tooltip", "Perfil de Estabilização do Traço (Estabilizador Lab)"))

        for pid, pdata in hub.PROFILES.items():
            icon = get_icon(pdata.get("icon_name", "stabilizer"), "FG_SECONDARY")
            self.combo_stabilizer.addItem(icon, pdata["name"], pid)

        idx = self.combo_stabilizer.findData(hub.current_profile)
        if idx >= 0:
            self.combo_stabilizer.setCurrentIndex(idx)

        self.combo_stabilizer.currentIndexChanged.connect(self._on_topbar_stabilizer_changed)
        hub.profileChanged.connect(self._sync_combo_from_hub)
        self.addWidget(self.combo_stabilizer)

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
        self.action_clear.setText(tr("tools.clean", "Limpar Tela"))
        self.action_clear.setToolTip(tr("tools.clean_tooltip", "Limpar todo o conteúdo do canvas"))

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

    def _on_topbar_stabilizer_changed(self, index: int) -> None:
        if hasattr(self, "combo_stabilizer"):
            pid = self.combo_stabilizer.currentData()
            if pid:
                from ui.core.engine.stabilizer_hub import StabilizerHub
                StabilizerHub.instance().set_profile(pid)

    def _sync_combo_from_hub(self, profile_id: str) -> None:
        if hasattr(self, "combo_stabilizer"):
            idx = self.combo_stabilizer.findData(profile_id)
            if idx >= 0 and self.combo_stabilizer.currentIndex() != idx:
                self.combo_stabilizer.blockSignals(True)
                self.combo_stabilizer.setCurrentIndex(idx)
                self.combo_stabilizer.blockSignals(False)
