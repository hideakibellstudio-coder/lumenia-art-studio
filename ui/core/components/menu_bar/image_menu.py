"""
ImageMenu — Menu Imagem (Padrão Profissional da Indústria) — ARCcC i18n.
========================================================================
Expõe ações de dimensionamento do canvas/imagem, cortes, rotações e ajustes rápidos de imagem.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.infrastructure.icons import get_icon
from ui.infrastructure.i18n import tr


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
        self.retranslate_ui()

    def setup_actions(self):
        # 1. Dimensões
        self.act_canvas_size = QtGui.QAction(get_icon("ruler"), "", self)
        self.act_canvas_size.setShortcut("Ctrl+Alt+C")
        self.act_canvas_size.triggered.connect(self.canvasSizeRequested.emit)
        self.addAction(self.act_canvas_size)

        self.act_img_size = QtGui.QAction(get_icon("image"), "", self)
        self.act_img_size.setShortcut("Ctrl+Alt+I")
        self.act_img_size.triggered.connect(self.imageSizeRequested.emit)
        self.addAction(self.act_img_size)

        self.act_crop = QtGui.QAction(get_icon("cut"), "", self)
        self.act_crop.triggered.connect(self.cropRequested.emit)
        self.addAction(self.act_crop)

        self.addSeparator()

        # 2. Rotações e Espelhamento do Canvas
        self.menu_rotate = QtWidgets.QMenu("", self)
        self.menu_rotate.setIcon(get_icon("rotate_cw"))

        self.act_r90cw = QtGui.QAction(get_icon("rotate_cw"), "", self)
        self.act_r90cw.triggered.connect(self.rotate90CWRequested.emit)
        self.menu_rotate.addAction(self.act_r90cw)

        self.act_r90ccw = QtGui.QAction(get_icon("rotate_ccw"), "", self)
        self.act_r90ccw.triggered.connect(self.rotate90CCWRequested.emit)
        self.menu_rotate.addAction(self.act_r90ccw)

        self.act_r180 = QtGui.QAction(get_icon("reset"), "", self)
        self.act_r180.triggered.connect(self.rotate180Requested.emit)
        self.menu_rotate.addAction(self.act_r180)

        self.addMenu(self.menu_rotate)

        self.act_fliph = QtGui.QAction(get_icon("flip_horizontal"), "", self)
        self.act_fliph.triggered.connect(self.flipHorizontalRequested.emit)
        self.addAction(self.act_fliph)

        self.act_flipv = QtGui.QAction(get_icon("flip_vertical"), "", self)
        self.act_flipv.triggered.connect(self.flipVerticalRequested.emit)
        self.addAction(self.act_flipv)

        self.addSeparator()

        # 3. Ajustes Rápidos de Cor
        self.menu_adjust = QtWidgets.QMenu("", self)
        self.menu_adjust.setIcon(get_icon("palette"))

        self.act_bc = QtGui.QAction(get_icon("sun"), "", self)
        self.act_bc.triggered.connect(self.brightnessContrastRequested.emit)
        self.menu_adjust.addAction(self.act_bc)

        self.act_hs = QtGui.QAction(get_icon("color_wheel"), "", self)
        self.act_hs.setShortcut("Ctrl+U")
        self.act_hs.triggered.connect(self.hueSaturationRequested.emit)
        self.menu_adjust.addAction(self.act_hs)

        self.act_invert = QtGui.QAction(get_icon("eye_off"), "", self)
        self.act_invert.setShortcut("Ctrl+I")
        self.act_invert.triggered.connect(self.invertColorsRequested.emit)
        self.menu_adjust.addAction(self.act_invert)

        self.addMenu(self.menu_adjust)

    def retranslate_ui(self):
        self.setTitle(tr("menu.image.title", "Imagem"))
        self.act_canvas_size.setText(tr("menu.image.canvas_size", "Tamanho do Canvas..."))
        self.act_img_size.setText(tr("menu.image.image_size", "Resolução da Imagem..."))
        self.act_crop.setText(tr("menu.image.crop", "Cortar pela Seleção"))
        self.menu_rotate.setTitle(tr("menu.image.rotate_menu", "Rotacionar Canvas"))
        self.act_r90cw.setText(tr("menu.image.rotate_90_cw", "90° Sentido Horário"))
        self.act_r90ccw.setText(tr("menu.image.rotate_90_ccw", "90° Sentido Anti-Horário"))
        self.act_r180.setText(tr("menu.image.rotate_180", "180°"))
        self.act_fliph.setText(tr("menu.image.flip_h", "Espelhar Canvas Horizontalmente"))
        self.act_flipv.setText(tr("menu.image.flip_v", "Espelhar Canvas Verticalmente"))
        self.menu_adjust.setTitle(tr("menu.image.adjustments", "Ajustes Rápidos"))
        self.act_bc.setText(tr("menu.filter.brightness_contrast", "Brilho e Contraste..."))
        self.act_hs.setText(tr("menu.filter.hue_saturation", "Matiz e Saturação..."))
        self.act_invert.setText(tr("menu.filter.invert", "Inverter Cores"))
