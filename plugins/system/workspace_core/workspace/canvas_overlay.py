"""
CanvasOverlay — Overlay de Interceptação de Eventos (Totalmente Invisível)
==========================================================================
Widget 100% transparente de interceptação de cliques para recolher gavetas flutuantes.
Nenhum escurecimento rasterizado de CPU é desenhado para manter o WGPU 100% limpo e cristalino.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class CanvasOverlay(QtWidgets.QWidget):
    """Overlay 100% invisível de interceptação de cliques sobre o canvas."""

    overlay_clicked = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        self.hide()

        if parent:
            parent.installEventFilter(self)

    def set_blocking(self, block: bool) -> None:
        """Exibe ou oculta a captura de clique invisível sobre o canvas."""
        if block:
            if self.parentWidget():
                self.setGeometry(self.parentWidget().rect())
            self.show()
            self.raise_()
        else:
            self.hide()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Sincroniza a geometria do overlay exatamente com o rect() do canvas_wrapper pai."""
        if watched is self.parentWidget() and event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.LayoutRequest):
            self.setGeometry(self.parentWidget().rect())
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Clique no canvas com gaveta flutuante aberta dispara o fechamento imediato."""
        if event.button() == QtCore.Qt.LeftButton:
            self.overlay_clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Sem qualquer escurecimento ou pintura visual para manter o canvas GPU 100% cristalino."""
        pass
