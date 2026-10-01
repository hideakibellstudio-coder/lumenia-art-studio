"""The pieces the brush engines and the layer file stand on, tested without Python (ARCcC 15.4, rule 5).

Until 2026-10-01 the engine had one isolated native test (history faults). The nine brush engines now
share `DabFootprint`, `PixelPermission`, `TipShape` and `StraightOver`, and the layer file format
rests on `TileGridCodec`; the bridge and the interface exercise them only through a whole stroke.
tests/native/dab_core_checks.cpp checks each directly:

  * the footprint of a dab visits exactly the pixels a brute-force scan finds inside the ellipse
    (round and flattened, rotated, at the canvas edge and with the circle just touching a tile);
  * selection and clipping base scale or refuse a pixel as documented;
  * opaque paint covers, Alpha Lock keeps the alpha and never paints on an empty pixel;
  * the tip is solid in the core, falls off monotonically and is zero outside the dab;
  * a layer survives encode and decode, and a truncated, mislabelled, wrong-sized or over-long block is
    refused without touching the grid.

Mutations of the row span, of the tile culling radius and of the clipping scale fail it.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def dab_core_harness():
    result = subprocess.run([sys.executable, str(ROOT / "tests/native/build_dab_core_checks.py")],
                            cwd=ROOT, capture_output=True, text=True, timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr
    from tests.native.build_dab_core_checks import BINARY
    return BINARY


def test_the_dab_core_and_the_tile_codec_hold_without_the_bridge(dab_core_harness):
    result = subprocess.run([str(dab_core_harness)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "dab core checks: all passed" in result.stdout
    assert "0 mismatching pixels" in result.stdout
