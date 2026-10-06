"""Build the composite projection harness with the same compiler family as the extension."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.native.harness_build import binary_path, build_harness  # noqa: E402

BINARY = binary_path("composite_projection_checks")
SOURCES = [
    "tests/native/composite_projection_checks.cpp",
    "tests/native/compositor_stale_checks.cpp",
    "engine/core/document/projection/CompositeProjection.cpp",
    "engine/core/canvas/Tile.cpp", "engine/core/canvas/TileGrid.cpp",
    "engine/core/canvas/SpatialCuller.cpp",
    "engine/infrastructure/compression/Lz4Codec.cpp",
    "engine/core/document/FilterLayer.cpp",
    "engine/core/document/Compositor.cpp",
    "engine/core/document/CompositeRegionSupport.cpp",
    "engine/core/document/GroupBlender.cpp",
    "engine/core/document/RegionBuffer.cpp",
    "engine/core/document/LayerCompositePass.cpp",
    "engine/core/document/blending/BlendKernel.cpp",
    "engine/core/document/blending/BlendKernelAvx2.cpp",
    "engine/core/document/blending/BlendKernel16.cpp",
    "engine/core/document/blending/BlendKernel16Avx2.cpp",
    "engine/core/color/DeepColorLut.cpp",
    "engine/core/color/LinearColorSpace16.cpp",
    "engine/core/document/filters/FilterApplier.cpp",
    "engine/core/document/filters/PointFilters.cpp",
    "engine/core/document/filters/AreaFilters.cpp",
    "engine/core/document/filters/AreaFilters16.cpp",
    "engine/core/document/filters/PointFilters16.cpp",
]


def build():
    build_harness("composite_projection_checks", SOURCES)


if __name__ == "__main__":
    os.chdir(ROOT)
    build()
