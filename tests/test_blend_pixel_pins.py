"""`blendPixel` gives the same pixel for every blend mode, gamma and depth (S2, Compositor seal).

`blendPixel` was one function with cyclomatic complexity 32 (the ARCcC 4.2 alert is 10); it is a
dispatcher over named paths now. The compositing golden only reaches the combinations of its eight
scenes, so the split is held by a native harness (tests/native/blend_pixel_pins.cpp) that hashes
4096 deterministic cases for each of the 13 modes x linear/sRGB x 8-bit/deep colour and compares
them with the hashes recorded from the implementation before the split. Mutations of the Add
equation and of the sRGB shortcut make it fail.

A deliberate change of the maths regenerates the table with `blend_pixel_pins --print`.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pins_harness():
    result = subprocess.run([sys.executable, str(ROOT / "tests/native/build_blend_pins.py")],
                            cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    from tests.native.build_blend_pins import BINARY
    return BINARY


def test_every_mode_gamma_and_depth_gives_the_recorded_pixels(pins_harness):
    result = subprocess.run([str(pins_harness)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "52 combinations match" in result.stdout
