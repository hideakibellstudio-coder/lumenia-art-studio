"""The row blend kernel and the Deep Color tables give the same pixels as their definitions (S2, Compositor foundation).

`BlendKernel::blendRow` composes a row of a layer onto the destination with a plan made once per layer, a
scalar loop and an AVX2 loop chosen by the CPU at run time; `DeepColorLut` replaces the nine `pow` calls per
pixel of the Deep Color path with exact tables. Both are exact: the native harness
(tests/native/blend_kernel_checks.cpp) compares them byte by byte with `blendPixel` and
`blendLinearNormalHighPrecision`: 24 million doubles around every step of the sRGB staircase, 6 million Deep
Color blends, every mode x gamma x depth x opacity x row length x alpha pattern at each SIMD level (with
guard pixels against writes outside the row) and 8 million pixels of a large buffer in odd-length rows.

Mutations that make it fail: the AVX2 or the scalar rounding of the 12-bit index, the cover threshold of
either loop, a nudged staircase threshold, an AVX2 loop that runs one pixel past the row, and routing the
sRGB plan to the linear loop.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def kernel_harness():
    result = subprocess.run([sys.executable, str(ROOT / "tests/native/build_blend_kernel_checks.py")],
                            cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    from tests.native.build_blend_kernel_checks import BINARY
    return BINARY


def test_rows_and_tables_equal_their_definitions_at_every_simd_level(kernel_harness):
    result = subprocess.run([str(kernel_harness)], capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    assert "deep lut: toLinear 256 values equal" in out
    assert "deep lut: 255 steps" in out
    assert "blends equal blendLinearNormalHighPrecision" in out
    assert "rows scalar: 33124 rows" in out
    # a CPU without AVX2 says so; the scalar level and the tables are checked either way
    assert "rows avx2: 33124 rows" in out or "rows avx2: skipped" in out
    assert "blend kernel checks: all equal" in out
