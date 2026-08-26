"""Thumbnails rendering helpers for Advanced Panel."""

from PySide6 import QtCore, QtGui

def create_default_shape_pixmap() -> QtGui.QPixmap:
    pm_shape = QtGui.QPixmap(46, 46)
    pm_shape.fill(QtGui.QColor(16, 16, 16))
    p = QtGui.QPainter(pm_shape)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    grad = QtGui.QRadialGradient(23, 23, 23)
    grad.setColorAt(0.0, QtGui.QColor(255, 255, 255, 255))
    grad.setColorAt(0.7, QtGui.QColor(255, 255, 255, 180))
    grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
    p.setBrush(QtGui.QBrush(grad))
    p.setPen(QtCore.Qt.NoPen)
    p.drawRect(0, 0, 46, 46)
    p.end()
    return pm_shape

def create_default_grain_pixmap() -> QtGui.QPixmap:
    pm_grain = QtGui.QPixmap(46, 46)
    pm_grain.fill(QtGui.QColor(24, 24, 32))
    p = QtGui.QPainter(pm_grain)
    p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 30), 1))
    for y in range(0, 46, 6):
        for x in range(0, 46, 6):
            if (x + y) % 12 == 0:
                p.drawRect(x, y, 4, 4)
    p.end()
    return pm_grain
