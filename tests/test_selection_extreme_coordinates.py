"""Rectangle, ellipse and polygon selections survive any coordinate the int API can carry.

Fuzzing the facade with invalid arguments (2026-10-01: every method, 12 seeds) found one method that took the
process down: `select_rect(2**31 - 1, 0, 1, 1)` computed `x + w - 1` in `int`. The rectangle and ellipse masks now
do their arithmetic in 64 bits (and the scan-line polygon clamps a crossing before turning it into an `int`).
The mouse can never produce such a coordinate, so this is not a bug the artist meets; it is the engine keeping its
promise that an out-of-range request is a refusal, not a crash, before something other than the mouse calls it.

The calls run in a child process: if the guarantee breaks, the test fails with the signal instead of killing pytest.
"""

from __future__ import annotations

import hashlib
import random
import subprocess
import sys
import textwrap
from pathlib import Path

import aladyn_engine_native as native

ROOT = Path(__file__).resolve().parents[1]

EXTREME_CALLS = textwrap.dedent("""
    import sys
    sys.path.insert(0, {root!r})
    import aladyn_engine_native as n
    f = n.PaintEngineFacade(64, 64)
    I, M = 2**31 - 1, -2**31
    print([
        f.select_rect(I, 0, 1, 1),
        f.select_rect(M, M, M, M, 1, 1000, 100000),
        f.select_rect(1, 2, I, 1000, 1, 1000, 100000),
        f.select_rect(0, 0, I, I, 0, 0, 0),
        f.select_rect(0, 0, I, I, 0, 0, I),
        f.select_ellipse(I, I, I, I, 0, True, I),
        f.select_ellipse(M, M, M, M, 0, False, 0),
        f.select_polygon([M, M, I, M, I, I, M, I], 0, False, 0),
        f.select_polygon([M, 0, I, 5, 0, I], 0, True, 3),
        f.select_polygon([0, 0, I, 1, 1, I], 0, False, 3),
    ])
""")


def test_extreme_coordinates_are_refused_or_clipped_never_a_crash():
    result = subprocess.run([sys.executable, "-c", EXTREME_CALLS.format(root=str(ROOT))],
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, f"the engine died (return code {result.returncode}): {result.stderr[-300:]}"
    # Off the canvas: nothing is selected. A rectangle or polygon that covers the canvas selects it (not the
    # one whose corner radius is 2**30: its rounded corner lies over the canvas).
    assert result.stdout.strip() == "[False, False, False, True, False, False, False, True, True, True]"


def _sane_hashes(calls: int) -> str:
    """The same scenes the old 32-bit code ran, hashed: the 64-bit rewrite must not move a pixel."""
    rng = random.Random(7)
    width, height = 97, 61
    digests = []
    for _ in range(calls):
        facade = native.PaintEngineFacade(width, height)
        kind = rng.choice(["rect", "ellipse", "poly_aa", "poly"])
        mode = rng.choice([0, 0, 1, 2, 3])
        feather = rng.choice([0, 0, 0, 2, 7])
        if kind == "rect":
            facade.select_rect(rng.randint(-40, 120), rng.randint(-40, 100), rng.randint(-60, 140), rng.randint(-60, 100),
                               0, feather, rng.choice([0, 0, 3, 12, 40, 500]))
        elif kind == "ellipse":
            facade.select_ellipse(rng.randint(-40, 140), rng.randint(-40, 100), rng.randint(-50, 80), rng.randint(-50, 80),
                                  0, rng.random() < 0.5, feather)
        else:
            points = []
            for _ in range(rng.randint(3, 9)):
                points += [rng.randint(-60, 160), rng.randint(-60, 120)]
            facade.select_polygon(points, 0, kind == "poly_aa", feather)
        facade.select_rect(rng.randint(0, 50), rng.randint(0, 40), rng.randint(5, 60), rng.randint(5, 40), mode, 0, 0)
        digests.append(hashlib.sha256(bytes(facade.get_selection_mask_buffer() or b"")).hexdigest()[:12])
    return hashlib.sha256("".join(digests).encode()).hexdigest()


def test_sane_selections_are_pixel_identical_to_the_32_bit_implementation():
    # Recorded with the build before the rewrite (6000 scenes were compared one by one; 800 are kept as the pin).
    assert _sane_hashes(800) == "e2dea9e6673727713c405d86a14d8099cf8986758bdfcbcb1706460e986a13e6"
