"""
FilterMenu — Menu Filtros (Padrão Profissional da Indústria) — ARCcC i18n.
==========================================================================
Expõe a galeria de filtros e ajustes de camada do Lumenia V2.
"""

from __future__ import annotations

from PySide6 import QtWidgets, QtGui, QtCore
from ui.core.icons import get_icon
from ui.core.i18n import tr


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
        self.retranslate_ui()

    def setup_actions(self):
        # 1. Galeria Completa de Filtros
        self.act_gallery = QtGui.QAction(get_icon("sparkles"), "", self)
        self.act_gallery.setShortcut("Ctrl+F")
        self.act_gallery.triggered.connect(self.filterGalleryRequested.emit)
        self.addAction(self.act_gallery)

        self.addSeparator()

        # 2. Desfoque & Pixelate
        self.act_blur = QtGui.QAction(get_icon("blur"), "", self)
        self.act_blur.triggered.connect(self.gaussianBlurRequested.emit)
        self.addAction(self.act_blur)

        self.act_pix = QtGui.QAction(get_icon("grid"), "", self)
        self.act_pix.triggered.connect(self.pixelateRequested.emit)
        self.addAction(self.act_pix)

        self.addSeparator()

        # 3. Ajustes de Cores
        self.act_hs = QtGui.QAction(get_icon("color_wheel"), "", self)
        self.act_hs.triggered.connect(self.hueSaturationFilterRequested.emit)
        self.addAction(self.act_hs)

        self.act_bc = QtGui.QAction(get_icon("sun"), "", self)
        self.act_bc.triggered.connect(self.brightnessContrastFilterRequested.emit)
        self.addAction(self.act_bc)

        self.act_cb = QtGui.QAction(get_icon("palette"), "", self)
        self.act_cb.triggered.connect(self.colorBalanceFilterRequested.emit)
        self.addAction(self.act_cb)

        self.act_inv = QtGui.QAction(get_icon("rotate_cw"), "", self)
        self.act_inv.triggered.connect(self.invertFilterRequested.emit)
        self.addAction(self.act_inv)

    def retranslate_ui(self):
        self.setTitle(tr("menu.filter.title", "Filtros"))
        self.act_gallery.setText(tr("menu.filter.adjustments", "Galeria de Filtros & Ajustes..."))
        self.act_blur.setText(tr("menu.filter.gaussian_blur", "Desfoque Gaussiano..."))
        self.act_pix.setText(tr("menu.filter.pixelate", "Pixelizar..."))
        self.act_hs.setText(tr("menu.filter.hue_saturation", "Matiz & Saturação..."))
        self.act_bc.setText(tr("menu.filter.brightness_contrast", "Brilho & Contraste..."))
        self.act_cb.setText(tr("menu.filter.color_balance", "Equilíbrio de Cores..."))
        self.act_inv.setText(tr("menu.filter.invert", "Inverter Cores"))
