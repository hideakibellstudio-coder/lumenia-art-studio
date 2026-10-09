"""Stabilized line with Windows input times: event stamps that repeat inside a ~15.6 ms tick.

Reported 2026-10-09, right after the stabilizer started weighing samples by age: straight
lines fine, circles with a zigzag edge. On Windows Qt stamps input with the message clock,
which advances in ticks: the owner's 125 Hz mouse arrives in pairs with one time (recorded
in tests/fixtures/mouse_circles_windows.jsonl with the arrival time of each event), a 1 kHz
mouse in groups of sixteen. Weighing a group as one instant made the stabilized line turn
1.4 to 1.9 times as much as the same input timed by arrival (2.2 to 4.7 times for the 1 kHz
circle below). The EventClock in the stabilizer spreads each group over its tick.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

native = pytest.importorskip("aladyn_engine_native", reason="native module not built here")

FIXTURE = Path(__file__).parent / "fixtures" / "mouse_circles_windows.jsonl"
TICK = 1.0 / 64.0  # GetMessageTime advances every 15.625 ms
MAX_EXTRA_TURNING = 1.03


def _stabilized_path(events: list[dict], stabilization: float, time_key: str) -> list[tuple[float, float]]:
    eng = native.PaintEngineFacade(1100, 800)
    eng.get_brush_profile().brush_size = 4.0
    stabilizer = eng.get_stabilizer()
    stabilizer.set_stabilization_percentage(stabilization)
    first = events[0]
    eng.begin_stroke_raw(first["x"], first["y"], 1.0, first[time_key])
    path = []
    for event in events[1:-1]:
        eng.update_stroke_raw(event["x"], event["y"], 1.0, event[time_key])
        point = stabilizer.get_stabilized_position()
        path.append((point.x, point.y))
    eng.end_stroke_raw(events[-1]["x"], events[-1]["y"])
    return path


def _turning(path: list[tuple[float, float]]) -> float:
    """Total absolute turning of the line, in radians: a zigzag adds turns that cancel out."""
    total, heading = 0.0, None
    for a, b in zip(path, path[1:]):
        if math.dist(a, b) < 0.5:
            continue
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        if heading is not None:
            total += abs((angle - heading + math.pi) % (2 * math.pi) - math.pi)
        heading = angle
    return total


def _extra_turning(events: list[dict], stabilization: float) -> float:
    stamped = _turning(_stabilized_path(events, stabilization, "ts"))
    timed = _turning(_stabilized_path(events, stabilization, "arr"))
    return stamped / timed


def _recorded() -> list[dict]:
    with FIXTURE.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


@pytest.mark.parametrize("index", range(4))
def test_recorded_windows_mouse_circles_have_no_zigzag(index):
    stroke = _recorded()[index]
    events = stroke["events"]
    stamps = [e["ts"] for e in events if e["k"] == "move"]
    assert len(set(stamps)) < 0.7 * len(stamps), "the fixture lost its repeated stamps"
    # Before the fix: 1.37 / 1.35 / 1.94 / 1.89.
    assert _extra_turning(events, stroke["stab"]) <= MAX_EXTRA_TURNING


def _ticked_circle(hz: float, lap_seconds: float = 0.5, laps: float = 2.0) -> list[dict]:
    count = int(lap_seconds * laps * hz)
    events = []
    for i in range(count + 1):
        t = i / hz
        angle = 2 * math.pi * t / lap_seconds - math.pi / 2
        events.append({"k": "move", "x": 350 + 250 * math.cos(angle), "y": 350 + 250 * math.sin(angle),
                       "arr": 500.0 + t, "ts": 500.0 + math.floor(t / TICK) * TICK})
    return events


@pytest.mark.parametrize("hz", [125, 1000])
@pytest.mark.parametrize("stabilization", [35.0, 70.0, 90.0])
def test_a_circle_with_ticked_stamps_matches_the_one_with_exact_times(hz, stabilization):
    # Before the fix at 1 kHz: 2.18 / 3.71 / 4.73.
    assert _extra_turning(_ticked_circle(hz), stabilization) <= MAX_EXTRA_TURNING

