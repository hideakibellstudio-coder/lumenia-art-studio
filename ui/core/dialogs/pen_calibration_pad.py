"""PressurePad — o quadro onde o artista desenha para o assistente medir a pressão BRUTA da caneta.

A pressão medida aqui é a que a mesa entrega, antes de qualquer curva (a do motor, a do
pincel): é ela que o assistente compara com a faixa 0..1. O mouse não tem pressão, então um
clique de mouse só avisa que é preciso usar a caneta; não entra no cálculo.
"""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.infrastructure.i18n import tr
from ui.infrastructure.theme import ThemeManager

# Quantos segmentos o quadro lembra para redesenhar (o suficiente para uns 20 traços longos).
MAX_TRAIL_SEGMENTS = 4000
MIN_STROKE_WIDTH = 1.0
MAX_STROKE_WIDTH = 10.0


class PressurePad(QtWidgets.QWidget):
    measured = QtCore.Signal()  # entrou ou saiu amostra: quem mostra o resumo relê `samples`

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PressurePad")
        self.setMinimumHeight(170)
        self.setCursor(QtCore.Qt.CrossCursor)
        self._samples: list[float] = []
        self._trail: list[tuple[QtCore.QPointF, QtCore.QPointF, float]] = []
        self._last: QtCore.QPointF | None = None
        self._mouse_used = False
        ThemeManager.instance().themeChanged.connect(self.update)

    @property
    def samples(self) -> list[float]:
        return list(self._samples)

    def feed(self, pressure: float) -> None:
        """Registra a pressão de um movimento da caneta (o `tabletEvent` chama isto)."""
        self._samples.append(float(pressure))
        self.measured.emit()

    def clear(self) -> None:
        self._samples.clear()
        self._trail.clear()
        self._last = None
        self._mouse_used = False
        self.update()
        self.measured.emit()

    def tabletEvent(self, event: QtGui.QTabletEvent) -> None:
        kind = event.type()
        if kind == QtCore.QEvent.TabletPress:
            self._last = event.position()
        elif kind == QtCore.QEvent.TabletMove and self._last is not None:
            point = event.position()
            pressure = float(event.pressure())
            self.feed(pressure)
            self._trail.append((self._last, point, pressure))
            del self._trail[:-MAX_TRAIL_SEGMENTS]
            self._last = point
            self.update()
        elif kind == QtCore.QEvent.TabletRelease:
            self._last = None
        event.accept()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.source() == QtCore.Qt.MouseEventNotSynthesized:
            self._mouse_used = True
            self.update()
        event.accept()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        theme = ThemeManager.instance()
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(theme.get_color("bg_card")))
        painter.setPen(QtGui.QPen(QtGui.QColor(theme.get_color("border")), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)

        ink = QtGui.QColor(theme.get_color("accent"))
        for start, end, pressure in self._trail:
            width = MIN_STROKE_WIDTH + (MAX_STROKE_WIDTH - MIN_STROKE_WIDTH) * max(0.0, min(1.0, pressure))
            painter.setPen(QtGui.QPen(ink, width, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
            painter.drawLine(start, end)

        if not self._trail:
            hint = (tr("dialogs.pen_pad_mouse", "O mouse não tem pressão: use a caneta neste quadro.")
                    if self._mouse_used else
                    tr("dialogs.pen_pad_hint", "Desenhe aqui como você desenha de verdade."))
            painter.setPen(QtGui.QColor(theme.get_color("text_sec")))
            painter.drawText(self.rect().adjusted(12, 12, -12, -12),
                             QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, hint)
        painter.end()
