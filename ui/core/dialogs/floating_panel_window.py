"""FloatingPanelWindow — janela de ajustes avançados que abre ao lado do canvas.

Base do painel avançado do pincel e do diálogo avançado de geometria: arrasta
pela própria janela e abre encostada na borda do canvas mais perto do botão
que a abriu, com a altura da área do workspace.

A área livre do canvas (entre as docas, em coordenadas globais) chega pelo
construtor (`canvas_area`, normalmente `WorkspaceService.canvas_area_rect`).
Até 2026-09-24 cada uma das duas janelas tinha sua cópia desta lógica e
achava as docas com `getattr(janela.workspace, "left_dock")`.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtCore, QtWidgets

from .floating_tool_window import FloatingToolWindow

CanvasAreaProvider = Callable[[], Optional[QtCore.QRect]]
_GAP = 10


class FloatingPanelWindow(FloatingToolWindow):
    def __init__(
        self,
        canvas_area: Optional[CanvasAreaProvider] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent, no_drop_shadow=True)
        self._canvas_area = canvas_area or (lambda: None)
        self._drag_pos: Optional[QtCore.QPoint] = None

    # ── Arrastar pela janela ──────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & QtCore.Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    # ── Abrir ao lado do canvas ───────────────────────────────────────────

    def show_beside_canvas(self, anchor: QtWidgets.QWidget, min_height: int) -> None:
        """Abre na borda do canvas do lado do `anchor` (botão que abriu a janela)."""
        screen = anchor.screen()
        scr = screen.availableGeometry() if screen else QtCore.QRect(0, 0, 1920, 1080)
        anchor_pos = anchor.mapToGlobal(QtCore.QPoint(0, 0))
        on_right = anchor_pos.x() > scr.center().x()
        area = self._canvas_area()
        if area is not None:
            y = area.y() + _GAP
            height = max(min_height, area.height() - 2 * _GAP)
            x = area.x() + area.width() - self.width() - _GAP if on_right else area.x() + _GAP
        else:  # sem workspace (testes, boot parcial): ao lado do próprio botão
            y = anchor_pos.y()
            height = max(min_height, scr.bottom() - y - 2 * _GAP)
            x = anchor_pos.x() - self.width() - _GAP if on_right else anchor_pos.x() + anchor.width() + _GAP

        height = min(height, scr.height() - 4 * _GAP)
        x = max(scr.left() + _GAP, min(x, scr.right() - self.width() - _GAP))
        if y + height > scr.bottom():
            y = max(scr.top() + _GAP, scr.bottom() - height - _GAP)
        self.setFixedHeight(height)
        self.move(QtCore.QPoint(x, y))
        self.show()
        self.raise_()
        self.activateWindow()
