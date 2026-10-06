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
    "engine/core/math/CurvilinearSnapEngine.cpp",
    "engine/core/math/SnapCandidate.cpp",
    "engine/core/math/TrajectoryEstimator.cpp",
    "engine/core/math/SnapLockStateMachine.cpp",
    "engine/core/math/ViewportTransform.cpp",
    "engine/core/stroke/VelocityTracker.cpp",
    "engine/core/stroke/DynamicStabilizer.cpp",
    "engine/core/brush/DynamicMapper.cpp",
    "engine/core/raster/DabInterpolator.cpp",
    "engine/core/raster/LargeBrushOptimizer.cpp",
    "engine/core/raster/DabRenderer.cpp",
    "engine/core/raster/DabFootprint.cpp",
    "engine/core/raster/StrokeOpacityMix.cpp",
    "engine/core/raster/StrokeInkLedger.cpp",
    "engine/core/raster/FloodFill.cpp",
    "engine/core/selection/SelectionEngine.cpp",
    "engine/core/selection/SelectionShapeMasks.cpp",
    "engine/core/selection/SelectionMorphology.cpp",
    "engine/core/raster/TransformEngine.cpp",
    "engine/core/raster/TransformEngineCommit.cpp",
    "engine/core/raster/TransformEngineDistort.cpp",
    "engine/core/canvas/SpatialCuller.cpp",
    "engine/core/canvas/Tile.cpp",
    "engine/core/canvas/TileGrid.cpp",
    "engine/core/canvas/TileGridCodec.cpp",
    "engine/core/history/TileUndoManager.cpp",
    "engine/core/history/TileHistoryRestore.cpp",
    "engine/infrastructure/storage/ScratchDiskManager.cpp",
    "engine/core/canvas/MipmapPyramid.cpp",
    "engine/infrastructure/compression/Lz4Codec.cpp",
    "engine/core/document/Compositor.cpp",
    "engine/core/document/CompositeRegionSupport.cpp",
    "engine/core/document/GroupBlender.cpp",
    "engine/core/document/RegionBuffer.cpp",
    "engine/core/document/projection/CompositeProjection.cpp",
    "engine/core/document/LayerCompositePass.cpp",
    "engine/core/document/blending/BlendKernel.cpp",
    "engine/core/document/blending/BlendKernelAvx2.cpp",
    "engine/core/document/blending/BlendKernel16.cpp",
    "engine/core/document/blending/BlendKernel16Avx2.cpp",
    "engine/core/document/filters/FilterApplier.cpp",
    "engine/core/document/filters/PointFilters.cpp",
    "engine/core/document/filters/AreaFilters.cpp",
    "engine/core/document/filters/AreaFilters16.cpp",
    "engine/core/document/filters/PointFilters16.cpp",
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
    "engine/core/color/DeepColorLut.cpp",
    "engine/core/color/LinearColorSpace16.cpp",
    "engine/boundary/orchestrator/StrokeOrchestrator.cpp",
    "engine/boundary/orchestrator/StrokeOrchestratorEnd.cpp",
    "engine/boundary/orchestrator/StrokeOrchestratorSegment.cpp",
    "engine/boundary/orchestrator/StrokePreviewRenderer.cpp",
    "engine/boundary/orchestrator/SelectionOrchestrator.cpp",
    "engine/boundary/orchestrator/TransformOrchestrator.cpp",
    "engine/boundary/orchestrator/BufferPasteOrchestrator.cpp",
    "engine/boundary/orchestrator/FloodFillOrchestrator.cpp",
    "engine/boundary/orchestrator/StrokeSessionOrchestrator.cpp",
    "engine/boundary/orchestrator/DocumentStateOrchestrator.cpp",
    "engine/boundary/orchestrator/SnapOrchestrator.cpp",
    "engine/boundary/orchestrator/RasterExportOrchestrator.cpp",
    "engine/boundary/public-api/PaintEngineFacade.cpp",
    "engine/boundary/public-api/PaintEngineFacadeDisplay.cpp",
    "engine/boundary/public-api/PaintEngineFacadePersistence.cpp",
    "engine/boundary/public-api/PaintEngineFacadeRgba16.cpp",
    "engine/boundary/public-api/PaintEngineFacadeLayers.cpp",
    "engine/boundary/public-api/LayerSnapshot.cpp",
    "engine/boundary/public-api/DecodedLayer.cpp",
    "engine/boundary/public-api/BrushPreviews.cpp",
    "bridge/core/bindings/bind_math_brush.cpp",
    "bridge/core/bindings/bind_canvas.cpp",
    "bridge/core/bindings/bind_layers.cpp",
    "bridge/core/bindings/bind_persistence.cpp",
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
