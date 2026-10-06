"""The storage of a 16-bit pixel and the pixel format of a document, without Python (S4).

A document has a pixel format, 8 bits per channel (the default, what the engine always stored) or 16. The native
harness (tests/native/pixel_format_checks.cpp and pixel_format_document_checks.cpp) checks, in both formats: the
channel conversion (every 8-bit value widens by x257 and narrows back to itself, every 16-bit value narrows to the
nearest 8-bit one), the PixelBuffer, the Tile (a 16-bit tile is empty only when every 16-bit alpha is 0), the TileGrid
(a resize with an offset equals the same resize of two 8-bit grids holding the high and the low byte of every channel),
the layer block codec (the header names the format, a block of another or unknown format, a truncated one and a raw tile
of the wrong size are refused without touching the grid), the layers a LayerStack makes, tile and structure history of a
16-bit document, and the guards that make each compositor and the merge refuse the other format.

Mutations that make it fail: `narrowChannel` truncating instead of rounding, `Tile::isEmpty` reading the 16-bit alpha as
8 bits, `resizePreserve` using 4 bytes a pixel, `copyFrom` keeping the old format, `decode` not comparing formats, the
codec header always writing 0, `commitStep` using the 8-bit zero tile, and the compositor format guard removed.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def format_harness():
    result = subprocess.run([sys.executable, str(ROOT / "tests/native/build_pixel_format_checks.py")],
                            cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    from tests.native.build_pixel_format_checks import BINARY
    return BINARY


def test_the_16bit_pixel_is_stored_converted_and_restored_exactly(format_harness):
    result = subprocess.run([str(format_harness)], capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    for line in (
        "conversion: 256 widen/narrow, 65536 narrow, 100000 colours, sizes and limits",
        "buffer: fill, views, size, reformat and resize in both formats",
        "tile: 16-bit emptiness, compression, adaptive view and shared buffer checked",
        "grid: 16-bit tiles, copy-on-write copy, 5 resizes equal their byte planes, prune and adoptTile checked",
        "codec RGBA8: header, round trip and refusals checked",
        "codec RGBA16: header, round trip and refusals checked",
        "codec: canvas limits per format and the decoded layer checked",
        "layers: background, layer, group, filter, duplicate, copy and resize follow the stack's format",
        "tile history: undo and redo of 16-bit tiles exact, an 8-bit sized snapshot refused",
        "structure history: undo and redo keep the 16-bit format and pixels",
        "guards: each compositor refuses the other format, the merge refuses a mixed stack",
        "pixel format checks: all equal",
    ):
        assert line in out
    assert "FAIL" not in out
