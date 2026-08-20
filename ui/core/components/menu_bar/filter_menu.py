"""
FilterMenu — Menu Filtros (Padrão Profissional da Indústria)
============================================================
Expõe a galeria de filtros e ajustes de camada do Lumenia V2.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon


class FilterMenu(QtWidgets.QMenu):
    filterGalleryRequested       = QtCore.Signal()
    gaussianBlurRequested        = QtCore.Signal()
    pixelateRequested            = QtCore.Signal()
    hueSaturationFilterRequested = QtCore.Signal()
    brightnessContrastFilterRequested = QtCore.Signal()
    colorBalanceFilterRequested  = QtCore.Signal()
    invertFilterRequested        = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("Filtros", parent)
        self.setup_actions()

    def setup_actions(self):
        # 1. Galeria Completa de Filtros
        act_gallery = QtGui.QAction(get_icon("sparkles"), "Galeria de Filtros & Ajustes...", self)
        act_gallery.setShortcut("Ctrl+F")
        act_gallery.triggered.connect(self.filterGalleryRequested.emit)
        self.addAction(act_gallery)

        self.addSeparator()

        # 2. Desfoque & Pixelate
        act_blur = QtGui.QAction(get_icon("blur"), "Desfoque Gaussiano (Blur)...", self)
        act_blur.triggered.connect(self.gaussianBlurRequested.emit)
        self.addAction(act_blur)

        act_pix = QtGui.QAction(get_icon("grid"), "Pixelizar (Mosaico 8-Bits)...", self)
        act_pix.triggered.connect(self.pixelateRequested.emit)
        self.addAction(act_pix)

        self.addSeparator()

        # 3. Ajustes de Cores
        act_hs = QtGui.QAction(get_icon("color_wheel"), "Matiz & Saturação...", self)
        act_hs.triggered.connect(self.hueSaturationFilterRequested.emit)
        self.addAction(act_hs)

        act_bc = QtGui.QAction(get_icon("sun"), "Brilho, Contraste & Gama...", self)
        act_bc.triggered.connect(self.brightnessContrastFilterRequested.emit)
        self.addAction(act_bc)

        act_cb = QtGui.QAction(get_icon("palette"), "Balanço de Cores (RGB)...", self)
        act_cb.triggered.connect(self.colorBalanceFilterRequested.emit)
        self.addAction(act_cb)

        act_inv = QtGui.QAction(get_icon("rotate_cw"), "Inversão / Limiar (Threshold)...", self)
        act_inv.triggered.connect(self.invertFilterRequested.emit)
        self.addAction(act_inv)
