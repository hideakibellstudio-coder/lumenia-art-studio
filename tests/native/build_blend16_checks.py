"""Build the 16-bit blend harness with the same compiler family as the extension."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.native.harness_build import binary_path, build_harness  # noqa: E402

BINARY = binary_path("blend16_checks")
SOURCES = [
    "tests/native/blend16_checks.cpp",
    "engine/core/document/blending/BlendKernel.cpp",
    "engine/core/document/blending/BlendKernelAvx2.cpp",
    "engine/core/document/blending/BlendKernel16.cpp",
    "engine/core/document/blending/BlendKernel16Avx2.cpp",
    "engine/core/color/LinearColorSpace16.cpp",
    "engine/core/color/DeepColorLut.cpp",
]


def build():
    build_harness("blend16_checks", SOURCES)


if __name__ == "__main__":
    os.chdir(ROOT)
    build()
