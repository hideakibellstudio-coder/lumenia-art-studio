"""The 16-bit compositor, without Python: the blend of a 16-bit pixel and the composition of a 16-bit document (S5).

A 16-bit document composes its layers in an internal 16-bit buffer and narrows to the 8-bit screen only the pixels it
composed. Two native harnesses measure it (their exit code is the failure count and they print what they measured):

  - `blend16_checks` (blend16_checks.cpp): the reference `blendPixel16` and the row kernel `BlendKernel16`. The sRGB
    tables (toLinear error, the interpolated encode within 0.25 of a step, the 16-bit round trip exact); the Normal rows
    in linear and sRGB gamma against the definition (at most 1 level of 16 bits, alpha exact, the full-alpha and
    transparent shortcuts exact), and the AVX2 row of Normal in linear gamma byte-equal to the scalar row; the other modes, which are the definition itself, exact over 12 modes x 2 gammas x 4
    opacities; and every mode against the 8-bit blend on 8-bit-exact values;
  - `compositor16_checks` (compositor16_checks.cpp, compositor16_lazy_checks.cpp, filter16_checks.cpp): whole documents.
    The same plan built as an 8-bit and as a widened 16-bit document (Normal stacks, other modes, groups, clipping masks,
    hidden layers, the seven filters), the 16-bit composite against a per-pixel model of the definition, the 16 bits
    that survive, the lazy projection (invalidate, read windows, byte-equal to a full composition), the merges and each
    filter on identical input.

Mutations that make it fail: the kernel's alpha divisor, the sRGB encode table, a clipping mask scaled by the wrong alpha,
the group origin of a window composed alone, `narrowRegion` skipping a row, the `RegionMargin` saved at 4 bytes a pixel, the filter
dispatch always taking the 8-bit path, the lazy region not widened by the filter reach.
"""
import re
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run(builder: str) -> str:
    built = subprocess.run([sys.executable, str(ROOT / f"tests/native/{builder}.py")],
                           cwd=ROOT, capture_output=True, text=True, timeout=600)
    assert built.returncode == 0, built.stdout + built.stderr
    binary = import_module(f"tests.native.{builder}").BINARY
    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAIL" not in result.stdout
    return result.stdout


def _worst(out: str, pattern: str) -> int:
    match = re.search(pattern, out)
    assert match, f"{pattern!r} not in the harness output:\n{out}"
    return int(match.group(1))


@pytest.fixture(scope="module")
def blend_output():
    return _run("build_blend16_checks")


@pytest.fixture(scope="module")
def compositor_output():
    return _run("build_compositor16_checks")


def test_the_16_bit_blend_kernel_follows_its_definition(blend_output):
    out = blend_output
    assert "round trip differs on 0 of 65536 (worst 0)" in out
    assert _worst(out, r"normal rows \(linear\): \d+ pixels, max difference (\d+) level") <= 1
    assert _worst(out, r"normal rows \(sRGB\): \d+ pixels, max difference (\d+) level") <= 1
    assert out.count("alpha differs on 0, shortcuts differ on 0") == 2
    assert ("identical to the scalar rows, guards untouched" in out) or ("this CPU has no AVX2" in out)
    assert ("other modes: 3840 rows (97536 pixels) of 12 modes x 2 gammas x 4 opacities equal the definition, "
            "guards untouched") in out
    assert out.count("against 8 bits:") == 13
    assert "blend16 checks: all within bounds" in out


def test_a_16_bit_document_composes_like_the_definition_and_like_the_8_bit_one(compositor_output):
    out = compositor_output
    assert _worst(out, r"normal stacks: 24 scenes, 16-bit composite vs the definition max (\d+) level") <= 1
    assert _worst(out, r"screen vs the 8-bit document max (\d+) level \(\d+\.\d+%\)\n") <= 3
    assert "other modes: 36 scenes of 12 modes over an opaque base, 16-bit composite equals the definition exactly" in out
    assert _worst(out, r"structures: 24 scenes .* vs the definition max (\d+) level") <= 1
    assert out.count("filters: type ") == 7
    assert "compositor16 checks: all within bounds" in out


def test_the_16_bits_survive_the_lazy_projection_the_merges_and_the_filters(compositor_output):
    out = compositor_output
    assert ("precision: a ramp of 300 values inside 2 eight-bit levels stays exact and distinct; "
            "translucent 16-bit layers match the definition within 1 level") in out
    assert ("laziness: 84 edits under a blur and a pixelate, 252 windows read, windows and whole canvas equal a full "
            "composition (16-bit buffer and screen)") in out
    assert ("laziness with groups: 80 edits under isolated and Pass Through groups and a clipping mask, "
            "240 windows read, each equal to a full composition") in out
    assert _worst(out, r"merge: 31 merges of a layer down max (\d+) level") == 0
    assert out.count("16-bit vs 8-bit on identical input") == 7
    assert ("filters: 68 runs (17 settings x 2 opacities x whole buffer and sub-rectangle); nothing outside the "
            "rectangle and no alpha-0 pixel changed") in out
