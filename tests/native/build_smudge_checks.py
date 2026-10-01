"""Build the smudge source-snapshot harness with the same compiler family as the extension."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.native.harness_build import binary_path, build_harness  # noqa: E402

BINARY = binary_path("smudge_source_snapshot")
SOURCES = [
    "tests/native/smudge_source_snapshot.cpp",
    "engine/core/engines/SmudgeEngine.cpp",
    "engine/core/canvas/Tile.cpp", "engine/core/canvas/TileGrid.cpp",
    "engine/core/canvas/SpatialCuller.cpp",
    "engine/infrastructure/compression/Lz4Codec.cpp",
    "engine/core/math/BezierCurve.cpp",
    "engine/core/texture/ProceduralTextures.cpp", "engine/core/texture/Texture2D.cpp",
]


def build():
    build_harness("smudge_source_snapshot", SOURCES)


if __name__ == "__main__":
    os.chdir(ROOT)
    build()
