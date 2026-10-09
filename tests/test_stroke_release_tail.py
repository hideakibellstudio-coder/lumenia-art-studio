"""Pen-up with stabilization: no chord, no tail past the release point, the same lag on every device.

Reported 2026-10-09: with stabilization on, the end of a stroke whipped and circles drawn
with the mouse never closed. Measured on the engine of that day (35%, 60 Hz mouse,
circle of radius 140 px): the stabilized line was 115 px behind at release (8 px with a
1 kHz mouse: the window counted events), the release drew a straight segment to the pen
and a 20 px taper went past it at 45 degrees from the real direction. These tests pin the
fix: a window of time, a pen-up that drains along the path, a taper inside the tail.
"""
from __future__ import annotations

import math

import pytest

native = pytest.importorskip("aladyn_engine_native", reason="native module not built here")

W = H = 360
CX = CY = 180.0
RADIUS = 140.0


def _circle(hz: float, seconds: float = 0.9) -> list[tuple[float, float, float]]:
    count = int(seconds * hz)
    return [(CX + RADIUS * math.cos(2 * math.pi * i / count - math.pi / 2),
             CY + RADIUS * math.sin(2 * math.pi * i / count - math.pi / 2), 10.0 + i / hz) for i in range(count + 1)]


def _engine(stabilization: float, size: float = 6.0, taper: bool = True):
    eng = native.PaintEngineFacade(W, H)
    profile = eng.get_brush_profile()
    profile.brush_size = size
    profile.stroke_taper_enabled = taper
    eng.get_stabilizer().set_stabilization_percentage(stabilization)
    return eng


def _draw(eng, samples, pressure: float = 1.0, release: bool = True) -> None:
    x0, y0, t0 = samples[0]
    eng.begin_stroke_raw(x0, y0, pressure, t0)
    for x, y, t in samples[1:-1]:
        eng.update_stroke_raw(x, y, pressure, t)
    if release:
        eng.end_stroke_raw(samples[-1][0], samples[-1][1])


def _ink(eng) -> list[tuple[int, int]]:
    buf = eng.get_pixel_buffer()
    return [(x, y) for y in range(H) for x in range(W) if buf[(y * W + x) * 4] < 128]


@pytest.mark.parametrize("hz", [60, 1000])
@pytest.mark.parametrize("stabilization", [35.0, 55.0, 80.0])
def test_a_mouse_circle_closes_without_a_chord_or_a_tail(stabilization, hz):
    eng = _engine(stabilization)
    _draw(eng, _circle(hz))
    radii = [math.hypot(x + 0.5 - CX, y + 0.5 - CY) for x, y in _ink(eng)]
    # Before the fix: the chord reached r ~ 100 and the extrapolated tail r ~ 150.
    assert min(radii) >= RADIUS - 10.0, "a straight segment cut across the circle"
    assert max(radii) <= RADIUS + 4.0, "ink beyond the circle: a tail past the release point"


def _lag_at_release(stabilization: float, hz: float) -> float:
    eng = _engine(stabilization)
    eng.set_telemetry_enabled(True)
    _draw(eng, _circle(hz), release=False)
    return eng.get_telemetry_snapshot().stabilizer_lag_px


@pytest.mark.parametrize("stabilization", [35.0, 80.0])
def test_the_lag_does_not_depend_on_how_often_the_device_reports(stabilization):
    lags = [_lag_at_release(stabilization, hz) for hz in (60, 125, 1000)]
    assert min(lags) > 1.0
    assert max(lags) / min(lags) < 1.6, f"lag by device rate 60/125/1000 Hz: {lags}"


def _line(speed_px_s: float = 2000.0, hz: float = 120.0) -> list[tuple[float, float, float]]:
    count = int(280.0 / speed_px_s * hz)
    return [(20.0 + 280.0 * i / count, CY, 5.0 + i / hz) for i in range(count + 1)]


def test_a_fast_line_never_paints_past_where_the_pen_lifted():
    eng = _engine(55.0, size=12.0)
    _draw(eng, _line())
    assert max(x for x, _ in _ink(eng)) <= 300 + 6 + 1


def test_the_tail_thins_toward_the_release_point():
    eng = _engine(55.0, size=12.0)
    _draw(eng, _line())
    ink = _ink(eng)
    def thickness(column: int) -> int:
        return sum(1 for x, _ in ink if x == column)
    assert thickness(296) < thickness(200), "the last px of the tail are as thick as the middle"


def test_without_taper_the_tail_keeps_its_width_and_still_stops_at_the_pen():
    eng = _engine(55.0, size=12.0, taper=False)
    _draw(eng, _line())
    ink = _ink(eng)
    assert max(x for x, _ in ink) <= 300 + 6 + 1
    assert sum(1 for x, _ in ink if x == 296) >= sum(1 for x, _ in ink if x == 200) - 1


def test_holding_still_settles_the_line_and_adds_no_ink():
    """What the canvas sends for a mouse held still (still_pointer.py): the same sample again."""
    eng = _engine(55.0, size=10.0)
    eng.set_telemetry_enabled(True)
    samples = _line(speed_px_s=1200.0)
    _draw(eng, samples, pressure=0.8, release=False)
    x, y, t = samples[-2]
    assert eng.get_telemetry_snapshot().stabilizer_lag_px > 5.0
    for _ in range(20):
        t += 1 / 60
        eng.update_stroke_raw(x, y, 0.8, t)
    assert eng.get_telemetry_snapshot().stabilizer_lag_px < 0.5
    settled = bytes(eng.get_pixel_buffer())
    for _ in range(40):
        t += 1 / 60
        eng.update_stroke_raw(x, y, 0.8, t)
    assert bytes(eng.get_pixel_buffer()) == settled, "holding still stamped the same spot again"


@pytest.mark.parametrize("stabilization", [35.0, 55.0])
def test_the_stabilized_path_does_not_bend_when_the_window_fills(stabilization):
    """Constant speed in, constant speed out: the count window jumped 25% the moment it filled."""
    stab = native.DynamicStabilizer(stabilization)
    stab.reset(native.Point2D(CX + RADIUS, CY), 1.0)
    points = []
    for i in range(1, 200):
        a = 2 * math.pi * i / 120
        p = stab.update(native.Point2D(CX + RADIUS * math.cos(a), CY + RADIUS * math.sin(a)), 1.0, 0.0)
        points.append((p.x, p.y))
    steps = [math.dist(points[i], points[i - 1]) for i in range(1, len(points))]
    assert max(steps[i] / steps[i - 1] for i in range(1, len(steps))) < 1.05
