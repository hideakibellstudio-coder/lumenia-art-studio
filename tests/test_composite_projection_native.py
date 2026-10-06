"""The projection of the composite buffer and the Compositor's stale-tile rules, without Python (S3).

`CompositeProjection` keeps a stale flag per 128x128 tile of the composite buffer; `Compositor` marks tiles stale
(`invalidate`, `invalidateAll`), recomposes only the stale tiles a rectangle touches (`ensureFresh`) and refreshes
whole tiles in the region composites. The native harness (tests/native/composite_projection_checks.cpp and
compositor_stale_checks.cpp) checks the projection against a model written another way after 4200 random operations
(canvases of 1 pixel to 1024, rectangles inside, across and outside, empty and inverted), and the Compositor on a
300x260 canvas: laziness, writes only to stale tiles, whole-tile region composites, the ink of a stroke over stale
tiles, and 40 scenes of random edits under a blur and a pixelate filter that always end equal to a full composition.

Mutations that make it fail: `markFresh` accepting a tile that is only partly inside the rectangle, `expandToStale`
returning the rectangle itself (the stroke ink is erased by the next read), `invalidate` ignoring the reach of the
filters, `staleRects` joining boxes that do not line up, and `ensureFresh` composing the whole canvas.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def projection_harness():
    result = subprocess.run([sys.executable, str(ROOT / "tests/native/build_composite_projection_checks.py")],
                            cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    from tests.native.build_composite_projection_checks import BINARY
    return BINARY


def test_the_projection_equals_its_model_and_the_compositor_recomposes_only_what_is_read(projection_harness):
    result = subprocess.run([str(projection_harness)], capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    for size in ("1x1", "127x129", "128x128", "129x127", "300x200", "513x257", "1024x1024"):
        assert f"projection {size}: 600 random operations equal the model" in out
    assert "filters: 40 scenes x 14 edits, full reads equal a full composition" in out
    assert "compositor: laziness, stale-only writes, whole-tile region composites, stroke ink and filters checked" in out
    assert "composite projection checks: all equal" in out
