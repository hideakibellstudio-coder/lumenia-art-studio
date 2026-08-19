"""
ImageMenu — Menu Imagem (Padrão Profissional da Indústria)
==========================================================
Expõe ações de dimensionamento do canvas/imagem, cortes, rotações e ajustes rápidos de imagem.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore


class ImageMenu(QtWidgets.QMenu):
    canvasSizeRequested       = QtCore.Signal()
    imageSizeRequested        = QtCore.Signal()
    cropRequested             = QtCore.Signal()
    rotate90CWRequested       = QtCore.Signal()
    rotate90CCWRequested      = QtCore.Signal()
    rotate180Requested        = QtCore.Signal()
    flipHorizontalRequested   = QtCore.Signal()
    flipVerticalRequested     = QtCore.Signal()
    brightnessContrastRequested = QtCore.Signal()
    hueSaturationRequested    = QtCore.Signal()
    invertColorsRequested     = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Imagem", parent)
        self.setup_actions()

    def setup_actions(self):
        # 1. Dimensões
        act_canvas_size = QtGui.QAction("📐 Tamanho do Canvas...", self)
        act_canvas_size.setShortcut("Ctrl+Alt+C")
        act_canvas_size.triggered.connect(self.canvasSizeRequested.emit)
        self.addAction(act_canvas_size)

        act_img_size = QtGui.QAction("🖼 Redimensionar Imagem...", self)
        act_img_size.setShortcut("Ctrl+Alt+I")
        act_img_size.triggered.connect(self.imageSizeRequested.emit)
        self.addAction(act_img_size)

        act_crop = QtGui.QAction("✂ Cortar pela Seleção", self)
        act_crop.triggered.connect(self.cropRequested.emit)
        self.addAction(act_crop)

        self.addSeparator()

        # 2. Rotações e Espelhamento do Canvas
        menu_rotate = QtWidgets.QMenu("🔄 Rotacionar Canvas", self)

        act_r90cw = QtGui.QAction("90° Sentido Horário", self)
        act_r90cw.triggered.connect(self.rotate90CWRequested.emit)
        menu_rotate.addAction(act_r90cw)

        act_r90ccw = QtGui.QAction("90° Sentido Anti-horário", self)
        act_r90ccw.triggered.connect(self.rotate90CCWRequested.emit)
        menu_rotate.addAction(act_r90ccw)

        act_r180 = QtGui.QAction("180°", self)
        act_r180.triggered.connect(self.rotate180Requested.emit)
        menu_rotate.addAction(act_r180)

        self.addMenu(menu_rotate)

        act_flip_h = QtGui.QAction("↔ Espelhar Horizontalmente", self)
        act_flip_h.setShortcut("H")
        act_flip_h.triggered.connect(self.flipHorizontalRequested.emit)
        self.addAction(act_flip_h)

        act_flip_v = QtGui.QAction("↕ Espelhar Verticalmente", self)
        act_flip_v.setShortcut("V")
        act_flip_v.triggered.connect(self.flipVerticalRequested.emit)
        self.addAction(act_flip_v)

        self.addSeparator()

        # 3. Ajustes Rápidos de Cor
        menu_adjust = QtWidgets.QMenu("🎨 Ajustes Rápidos", self)

        act_bright = QtGui.QAction("Brilho & Contraste...", self)
        act_bright.triggered.connect(self.brightnessContrastRequested.emit)
        menu_adjust.addAction(act_bright)

        act_hue = QtGui.QAction("Matiz & Saturação...", self)
        act_hue.triggered.connect(self.hueSaturationRequested.emit)
        menu_adjust.addAction(act_hue)

        act_inv = QtGui.QAction("Inverter Cores", self)
        act_inv.setShortcut("Ctrl+I")
        act_inv.triggered.connect(self.invertColorsRequested.emit)
        menu_adjust.addAction(act_inv)

        self.addMenu(menu_adjust)
