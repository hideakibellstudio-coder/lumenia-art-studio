"""PointerSample — o que o canvas precisa de um evento de mouse ou caneta.

Lê do evento Qt a posição, a pressão, o botão, a inclinação, a rotação, se a
ponta é a borracha e o instante (em segundos). O `RenderWidget` repassa a
amostra ao `CanvasInputRouter`. Extraído do `RenderWidget.tabletEvent` em
2026-09-24 (o widget passava de 400 linhas).
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from PySide6 import QtCore, QtGui


_last_known_offset: float | None = None


def event_time(event: QtGui.QInputEvent) -> float:
    """Instante do evento em segundos com alinhamento monotônico entre Qt e perf_counter."""
    global _last_known_offset
    stamp = event.timestamp()
    now_perf = time.perf_counter()
    if stamp > 0:
        stamp_sec = stamp / 1000.0
        _last_known_offset = stamp_sec - now_perf
        return stamp_sec
    if _last_known_offset is not None:
        return now_perf + _last_known_offset
    return now_perf


@dataclass(frozen=True)
class PointerSample:
    position: QtCore.QPointF
    button: QtCore.Qt.MouseButton
    pressure: float
    is_eraser: bool
    timestamp: float
    tilt_x: float
    tilt_y: float
    twist: float

    @classmethod
    def from_tablet(cls, event: QtGui.QTabletEvent) -> "PointerSample":
        device = event.pointingDevice()
        is_eraser = bool(device) and device.pointerType() == QtGui.QPointingDevice.PointerType.Eraser
        button = event.button() if event.button() != QtCore.Qt.NoButton else QtCore.Qt.LeftButton
        return cls(
            position=event.position(),
            button=button,
            pressure=event.pressure(),
            is_eraser=is_eraser,
            timestamp=event_time(event),
            tilt_x=float(event.xTilt()),
            tilt_y=float(event.yTilt()),
            twist=float(event.rotation()),
        )
