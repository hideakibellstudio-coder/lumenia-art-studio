"""The smudge trail reads the layer as it was when the dab arrived (D15, found 2026-10-01).

SmudgeEngine sampled the trail from the live TileGrid while it wrote the dab into
the same grid. Where the sample lies ahead in scan order (a stroke going up and to
the right) it read pixels the dab had just written, so the same stroke came out
different when the scene sat across other tile seams. Painting the same picture
64 px to the side must give the same picture.

The check is a native C++ harness (tests/native/smudge_source_snapshot.cpp) that runs
both directions of travel, because a stroke going down and to the right never
triggered it and a test with only that direction passed on the broken engine.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def smudge_harness():
    result = subprocess.run([sys.executable, str(ROOT / "tests/native/build_smudge_checks.py")],
                            cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    from tests.native.build_smudge_checks import BINARY
    return BINARY


def test_the_smudge_result_does_not_depend_on_where_the_tile_seams_fall(smudge_harness):
    result = subprocess.run([str(smudge_harness)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "direction 1: order independent" in result.stdout
    assert "direction -1: order independent" in result.stdout
