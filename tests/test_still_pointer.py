"""StillPointerFeeder: a mouse held still keeps reaching the stabilizer, and only while it is held."""
from __future__ import annotations

from ui.plugins.system.workspace_core.workspace.canvas.viewport.still_pointer import (
    SETTLED_AFTER_S, STILL_AFTER_S, HeldInput, StillPointerFeeder,
)


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _feeder(qapp):
    clock, fed = Clock(), []
    feeder = StillPointerFeeder(lambda held, stamp: fed.append((held.screen_x, stamp)), clock=clock)
    return feeder, clock, fed


def test_nothing_is_fed_while_events_keep_arriving(qapp):
    feeder, clock, fed = _feeder(qapp)
    feeder.start(HeldInput(10.0, 20.0, 0.7, 5.0))
    clock.now += STILL_AFTER_S / 2
    feeder.tick()
    assert fed == [] and feeder.running
    feeder.stop()


def test_a_held_pointer_is_repeated_with_the_time_it_has_been_held(qapp):
    feeder, clock, fed = _feeder(qapp)
    feeder.start(HeldInput(10.0, 20.0, 0.7, 5.0))
    clock.now += 0.05
    feeder.tick()
    ((x, stamp),) = fed
    assert x == 10.0 and abs(stamp - 5.05) < 1e-9
    feeder.stop()


def test_unknown_event_time_stays_unknown(qapp):
    feeder, clock, fed = _feeder(qapp)
    feeder.start(HeldInput(1.0, 1.0, 1.0, 0.0))
    clock.now += 0.05
    feeder.tick()
    assert fed == [(1.0, 0.0)]
    feeder.stop()


def test_ticks_pause_once_settled_and_resume_when_the_pointer_moves(qapp):
    feeder, clock, fed = _feeder(qapp)
    feeder.start(HeldInput(1.0, 1.0, 1.0, 5.0))
    clock.now += SETTLED_AFTER_S + 0.1
    feeder.tick()
    assert fed == [] and not feeder.running
    feeder.note(HeldInput(2.0, 1.0, 1.0, 5.7))
    assert feeder.running
    feeder.stop()


def test_after_the_stroke_nothing_is_fed(qapp):
    feeder, clock, fed = _feeder(qapp)
    feeder.start(HeldInput(1.0, 1.0, 1.0, 5.0))
    feeder.stop()
    feeder.note(HeldInput(2.0, 1.0, 1.0, 5.1))
    clock.now += 0.05
    feeder.tick()
    assert fed == [] and not feeder.running
