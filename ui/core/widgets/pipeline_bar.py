"""
PipelineBar — Barra empilhada proporcional colorida para decomposição do pipeline nativo C++.
============================================================================================
Estágios: Cinemática, Interpolação, Raster Dab, Undo, Compositor e Blit Viewport.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.infrastructure.theme.manager import ThemeManager


class PipelineBar(QtWidgets.QWidget):
    """Barra empilhada proporcional colorida para decomposição dos estágios do pipeline."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(12)
        self._values = [0.0] * 6

        tm = ThemeManager.instance()
        self.STAGES = [
            ("Cin", tm.get_color("TELEMETRY_STAGE_KINEMATICS", "#38bdf8"), "Cinemática e Estabilização"),
            ("Int", tm.get_color("TELEMETRY_STAGE_INTERPOLATION", "#facc15"), "Interpolação de Dabs"),
            ("Dab", tm.get_color("TELEMETRY_STAGE_RASTER", "#f97316"), "Rasterização de Carimbos"),
            ("Und", tm.get_color("TELEMETRY_STAGE_UNDO", "#a855f7"), "Gravação de Undo (Tiles)"),
            ("Cmp", tm.get_color("TELEMETRY_STAGE_COMPOSITOR", "#22c55e"), "Composição de Camadas"),
            ("Blt", tm.get_color("TELEMETRY_STAGE_BLIT", "#ec4899"), "Apresentação Viewport Qt (Blit)"),
        ]

    def set_values_us(self, kin: float, interp: float, dab: float, undo: float, comp: float, blit: float) -> None:
        self._values = [max(0.0, float(v)) for v in (kin, interp, dab, undo, comp, blit)]
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        rect = self.rect()
        total = sum(self._values)

        # Fundo do trilho
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 50))
        painter.drawRoundedRect(rect, 3, 3)

        if total <= 0.001:
            painter.end()
            return

        w = float(rect.width())
        x = float(rect.x())
        h = float(rect.height())

        for idx, val in enumerate(self._values):
            if val <= 0.0:
                continue
            seg_w = max(1.5, (val / total) * w)
            if x + seg_w > rect.right():
                seg_w = rect.right() - x
            _, col_hex, _ = self.STAGES[idx]
            painter.setBrush(QtGui.QColor(col_hex))
            painter.drawRect(QtCore.QRectF(x, 0.0, seg_w, h))
            x += seg_w
            if x >= rect.right():
                break

        painter.end()
