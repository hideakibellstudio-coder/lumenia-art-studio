"""StillPointerFeeder — a pointer held still keeps reaching the engine while the stroke lasts.

A mouse sends no event while it does not move, and the stabilizer only advances on
events: with the button held, the stabilized line stopped wherever it was, tens of
pixels behind the cursor, and jumped when the mouse moved again (measured
2026-10-09: 115 px at 35% with a 60 Hz mouse, before the time window). While a
stroke lasts, this collaborator repeats the last input every 16 ms once nothing new
has arrived for 20 ms, with the timestamp advanced by the time it has been held,
so the line settles under the cursor as the window runs out. A pen that keeps
reporting while pressed never triggers it. After half a second held the line has
long settled (the widest window is 0.2 s) and the ticks pause until the pointer
moves again; the timer belongs to the canvas widget and dies with it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6 import QtCore

TICK_MS = 16
STILL_AFTER_S = 0.020
SETTLED_AFTER_S = 0.5


@dataclass(frozen=True)
class HeldInput:
    screen_x: float
    screen_y: float
    pressure: float
    timestamp: float  # seconds, the event's own clock; 0 = unknown
    tilt_x: float = 0.0
    tilt_y: float = 0.0
    twist: float = 0.0


class StillPointerFeeder:
    def __init__(self, feed: Callable[[HeldInput, float], None], parent: Optional[QtCore.QObject] = None,
                 clock: Callable[[], float] = time.perf_counter) -> None:
        self._feed = feed
        self._clock = clock
        self._last: Optional[HeldInput] = None
        self._last_at = 0.0
        self._timer = QtCore.QTimer(parent)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self.tick)

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    def start(self, held: HeldInput) -> None:
        self._last = held
        self._last_at = self._clock()
        self._timer.start()

    def note(self, held: HeldInput) -> None:
        """A real event arrived: the pointer is where it says, at the time it says."""
        if self._last is None:
            return  # no stroke
        self._last = held
        self._last_at = self._clock()
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._last = None

    def tick(self) -> None:
        if self._last is None:
            return
        held_for = self._clock() - self._last_at
        if held_for < STILL_AFTER_S:
            return
        if held_for > SETTLED_AFTER_S:
            self._timer.stop()  # settled; the next real event starts it again
            return
        stamp = self._last.timestamp + held_for if self._last.timestamp > 0 else 0.0
        self._feed(self._last, stamp)
