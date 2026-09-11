import os

from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext


SIMD_MODE = os.environ.get("LUMENIA_SIMD", "scalar").strip().lower()
if SIMD_MODE not in {"scalar", "avx2"}:
    raise RuntimeError("LUMENIA_SIMD deve ser 'scalar' ou 'avx2'")

compile_args = ["/EHsc", "/bigobj", "/std:c++20", "/openmp", "/O2"]
# Um módulo CPython compilado globalmente para AVX2 pode falhar ao carregar em
# máquinas x64 sem essa extensão. O caminho base é escalar/SSE2 do x64; builds
# de laboratório podem pedir AVX2 explicitamente e devem ser distribuídos como
# artefatos separados.
if SIMD_MODE == "avx2":
    compile_args.append("/arch:AVX2")

cpp_sources = [
    "engine/core/math/BezierCurve.cpp",
    "engine/core/math/SymmetryEngine.cpp",
    "engine/core/math/GuideSnapEngine.cpp",
    "engine/core/math/ViewportTransform.cpp",
    "engine/core/stroke/VelocityTracker.cpp",
    "engine/core/stroke/DynamicStabilizer.cpp",
    "engine/core/brush/DynamicMapper.cpp",
    "engine/core/raster/DabInterpolator.cpp",
    "engine/core/raster/DabRenderer.cpp",
    "engine/core/raster/FloodFill.cpp",
    "engine/core/raster/SelectionEngine.cpp",
    "engine/core/raster/TransformEngine.cpp",
    "engine/core/canvas/SpatialCuller.cpp",
    "engine/core/canvas/Tile.cpp",
    "engine/core/canvas/TileGrid.cpp",
    "engine/core/canvas/TileUndoManager.cpp",
    "engine/core/canvas/TileHistoryRestore.cpp",
    "engine/core/canvas/ScratchDiskManager.cpp",
    "engine/core/canvas/MipmapPyramid.cpp",
    "engine/core/compression/Lz4Codec.cpp",
    "engine/core/document/Compositor.cpp",
    "engine/core/document/blending/FilterApplier.cpp",
    "engine/core/document/LayerStack.cpp",
    "engine/core/document/LayerMerger.cpp",
    "engine/core/document/FilterLayer.cpp",
    "engine/core/texture/Texture2D.cpp",
    "engine/core/texture/ProceduralTextures.cpp",
    "engine/core/engines/PencilEngine.cpp",
    "engine/core/engines/InkerEngine.cpp",
    "engine/core/engines/EraserEngine.cpp",
    "engine/core/engines/MarkerEngine.cpp",
    "engine/core/engines/BlurEngine.cpp",
    "engine/core/engines/SmudgeEngine.cpp",
    "engine/core/engines/WatercolorEngine.cpp",
    "engine/core/engines/OilImpastoEngine.cpp",
    "engine/core/color/ColorProfile.cpp",
    "engine/boundary/public-api/internal/StrokeOrchestrator.cpp",
    "engine/boundary/public-api/internal/SelectionOrchestrator.cpp",
    "engine/boundary/public-api/internal/TransformOrchestrator.cpp",
    "engine/boundary/public-api/internal/BufferPasteOrchestrator.cpp",
    "engine/boundary/public-api/internal/FloodFillOrchestrator.cpp",
    "engine/boundary/public-api/PaintEngineFacade.cpp",
    "bridge/core/bindings/bind_math_brush.cpp",
    "bridge/core/bindings/bind_canvas.cpp",
    "bridge/core/bindings/bind_layers.cpp",
    "bridge/core/bindings/bind_stroke.cpp",
    "bridge/core/bindings/bind_tools.cpp",
    "bridge/core/bindings/engine_bindings.cpp",
]

ext_modules = [
    Pybind11Extension(
        "aladyn_engine_native",
        cpp_sources,
        cxx_std=20,
        extra_compile_args=compile_args,
    ),
]

setup(
    name="aladyn_engine_native",
    version="0.2.0",
    author="Aladyn Team",
    description="Unified Native C++ Paint Engine for Lumenia",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
