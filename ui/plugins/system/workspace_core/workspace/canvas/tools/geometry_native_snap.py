"""NativeGeometrySnap — snap de perspectiva e curvilíneo calculado pelo motor C++.

Caminho opcional (Fase C3.2), ligado por `LUMENIA_SNAP_NATIVE_PERSPECTIVE=1`
e `LUMENIA_SNAP_NATIVE_CURVILINEAR=1`, para comparar o "feel" do nativo com o
Python antes de trocar o padrão. Colaborador com estado próprio do
`GeometryToolController`: até 2026-09-24 este estado (índice travado,
candidatas e âncoras) morava solto no controlador, que o chegava perto da
parede dos 450 linhas.

Âncora (Fase C3.5): depois de travar, a referência de direção para
re-travar é o último ponto travado, não o ponto de pressão — num traço longo
e rápido a corda até a pressão fica desatualizada e o re-lock errava.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from PySide6 import QtCore

from ui.core.engine.backend_protocols import GeometryProtocol


def first_not_none(*values):
    """Primeiro valor que não é None. Não use `a or b` com QPointF: o PySide6
    trata QPointF(0, 0) como falso e descartaria um ponto válido na origem
    (bug real da Fase C3.5)."""
    for value in values:
        if value is not None:
            return value
    return None


class NativeGeometrySnap:
    def __init__(self, backend: Callable[[], Optional[GeometryProtocol]]) -> None:
        self._backend = backend
        self.use_perspective = os.environ.get("LUMENIA_SNAP_NATIVE_PERSPECTIVE", "0") == "1"
        self.use_curvilinear = os.environ.get("LUMENIA_SNAP_NATIVE_CURVILINEAR", "0") == "1"
        self.reset()

    def reset(self) -> None:
        """Novo traço (ou fim dele): esquece trava, candidatas e âncoras."""
        self.curv_locked_index = -1
        self.stroke_candidates: list[float] = []
        self.curv_anchor: Optional[QtCore.QPointF] = None
        self.persp_anchor: Optional[QtCore.QPointF] = None

    def perspective(self, raw_x: float, raw_y: float, zoom: float, start: Optional[QtCore.QPointF],
                    locked_dir: Optional[tuple[float, float]]):
        """((x, y), nova direção travada ou None); None sem motor."""
        backend = self._backend()
        if backend is None:
            return None
        anchor = first_not_none(self.persp_anchor, start, QtCore.QPointF(raw_x, raw_y))
        has_lock = locked_dir is not None
        ldx, ldy = locked_dir if has_lock else (0.0, 0.0)
        x, y, has_lock_out, ndx, ndy = backend.snap_perspective(
            raw_x, raw_y, anchor.x(), anchor.y(), has_lock, ldx, ldy, zoom
        )
        if not has_lock_out:
            return (x, y), None
        self.persp_anchor = QtCore.QPointF(x, y)
        return (x, y), (ndx, ndy)

    def curvilinear(self, raw_x: float, raw_y: float, zoom: float, start: Optional[QtCore.QPointF],
                    is_stroking: bool):
        """(x, y) projetado na curva travada; None sem motor."""
        backend = self._backend()
        if backend is None:
            return None
        press_start = first_not_none(start, QtCore.QPointF(raw_x, raw_y))
        candidates = self.stroke_candidates if (is_stroking and self.stroke_candidates) else (
            backend.get_curvilinear_candidates(press_start.x(), press_start.y())
        )
        # As candidatas do traço inteiro vêm da pressão; só a referência de
        # direção para pontuar e re-travar usa a âncora recente.
        anchor = first_not_none(self.curv_anchor, press_start)
        x, y, new_index = backend.snap_curvilinear(
            raw_x, raw_y, anchor.x(), anchor.y(), candidates, self.curv_locked_index, is_stroking, zoom
        )
        if new_index >= 0:
            self.curv_locked_index = int(new_index)
            self.stroke_candidates = candidates
            self.curv_anchor = QtCore.QPointF(x, y)
        return (x, y)
