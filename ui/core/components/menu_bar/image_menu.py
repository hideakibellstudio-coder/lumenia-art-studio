"""
ImageMenu — Menu Imagem (Padrão Profissional da Indústria)
==========================================================
Expõe ações de dimensionamento do canvas/imagem, cortes, rotações e ajustes rápidos de imagem.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon


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
        act_canvas_size = QtGui.QAction(get_icon("ruler"), "Tamanho do Canvas...", self)
        act_canvas_size.setShortcut("Ctrl+Alt+C")
        act_canvas_size.triggered.connect(self.canvasSizeRequested.emit)
        self.addAction(act_canvas_size)

        act_img_size = QtGui.QAction(get_icon("image"), "Redimensionar Imagem...", self)
        act_img_size.setShortcut("Ctrl+Alt+I")
        act_img_size.triggered.connect(self.imageSizeRequested.emit)
        self.addAction(act_img_size)

        act_crop = QtGui.QAction(get_icon("cut"), "Cortar pela Seleção", self)
        act_crop.triggered.connect(self.cropRequested.emit)
        self.addAction(act_crop)

        self.addSeparator()

        # 2. Rotações e Espelhamento do Canvas
        menu_rotate = QtWidgets.QMenu("Rotacionar Canvas", self)
        menu_rotate.setIcon(get_icon("rotate_cw"))

        act_r90cw = QtGui.QAction(get_icon("rotate_cw"), "90° Sentido Horário", self)
        act_r90cw.triggered.connect(self.rotate90CWRequested.emit)
        menu_rotate.addAction(act_r90cw)

        act_r90ccw = QtGui.QAction(get_icon("rotate_ccw"), "90° Sentido Anti-horário", self)
        act_r90ccw.triggered.connect(self.rotate90CCWRequested.emit)
        menu_rotate.addAction(act_r90ccw)

        act_r180 = QtGui.QAction(get_icon("reset"), "180°", self)
        act_r180.triggered.connect(self.rotate180Requested.emit)
        menu_rotate.addAction(act_r180)

        self.addMenu(menu_rotate)

        act_fliph = QtGui.QAction(get_icon("flip_horizontal"), "Espelhar Canvas Horizontalmente", self)
        act_fliph.triggered.connect(self.flipHorizontalRequested.emit)
        self.addAction(act_fliph)

        act_flipv = QtGui.QAction(get_icon("flip_vertical"), "Espelhar Canvas Verticalmente", self)
        act_flipv.triggered.connect(self.flipVerticalRequested.emit)
        self.addAction(act_flipv)

        self.addSeparator()

        # 3. Ajustes Rápidos de Cor
        menu_adjust = QtWidgets.QMenu("Ajustes Rápidos", self)
        menu_adjust.setIcon(get_icon("palette"))

        act_bc = QtGui.QAction(get_icon("sun"), "Brilho / Contraste...", self)
        act_bc.triggered.connect(self.brightnessContrastRequested.emit)
        menu_adjust.addAction(act_bc)

        act_hs = QtGui.QAction(get_icon("color_wheel"), "Matiz / Saturação...", self)
        act_hs.setShortcut("Ctrl+U")
        act_hs.triggered.connect(self.hueSaturationRequested.emit)
        menu_adjust.addAction(act_hs)

        act_invert = QtGui.QAction(get_icon("eye_off"), "Inverter Cores", self)
        act_invert.setShortcut("Ctrl+I")
        act_invert.triggered.connect(self.invertColorsRequested.emit)
        menu_adjust.addAction(act_invert)

        self.addMenu(menu_adjust)
