#include "TransformOrchestrator.hpp"
#include "PixelFormatGuard.hpp"

namespace aladyn::engine::boundary::orchestrator {

bool TransformOrchestrator::beginTransform(
    raster::TransformEngine& transformEngine,
    document::LayerStack& layerStack,
    const selection::SelectionMask& selectionMask,
    history::TileUndoManager& undoManager,
    int canvasWidth, int canvasHeight
) {
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) {
        return false;
    }

    const selection::SelectionMask* pMask = selectionMask.hasSelection() ? &selectionMask : nullptr;
    return transformEngine.beginTransform(
        activeLayer, pMask, canvasWidth, canvasHeight, undoManager, layerStack.getActiveIndex()
    );
}

bool TransformOrchestrator::commitTransform(
    raster::TransformEngine& transformEngine,
    document::LayerStack& layerStack,
    history::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor,
    double dx, double dy, double scaleX, double scaleY,
    double rotationDeg, double pivotX, double pivotY,
    bool flipH, bool flipV, int interpMode,
    int canvasWidth, int canvasHeight
) {
    if (!transformEngine.isActive()) return false;
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer) return false;

    utils::Rect2D dirtyBounds;
    bool ok = transformEngine.commitTransform(
        activeLayer, dx, dy, scaleX, scaleY, rotationDeg, pivotX, pivotY,
        flipH, flipV, interpMode, canvasWidth, canvasHeight,
        undoManager, layerStack.getActiveIndex(), dirtyBounds
    );

    if (ok) {
        undoManager.commitStep(layerStack);
        compositor.compositeRegion(layerStack.getAllLayersForComposition(), dirtyBounds, outputBuffer, bgColor);
    }
    return ok;
}

bool TransformOrchestrator::commitTransformDistort(
    raster::TransformEngine& transformEngine,
    document::LayerStack& layerStack,
    history::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor,
    const std::array<double, 8>& corners, int interpMode,
    int canvasWidth, int canvasHeight
) {
    if (!transformEngine.isActive()) return false;
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer) return false;

    utils::Rect2D dirtyBounds;
    const bool ok = transformEngine.commitTransformDistort(
        activeLayer, corners, interpMode, canvasWidth, canvasHeight,
        undoManager, layerStack.getActiveIndex(), dirtyBounds
    );
    if (ok) {
        undoManager.commitStep(layerStack);
        compositor.compositeRegion(layerStack.getAllLayersForComposition(), dirtyBounds, outputBuffer, bgColor);
        return true;
    }
    cancelTransform(transformEngine, layerStack, undoManager, compositor, outputBuffer, bgColor);
    return false;
}

bool TransformOrchestrator::cancelTransform(
    raster::TransformEngine& transformEngine,
    document::LayerStack& layerStack,
    history::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
) {
    if (!transformEngine.isActive()) return false;
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer) return false;

    utils::Rect2D dirtyBounds;
    bool ok = transformEngine.cancelTransform(activeLayer, dirtyBounds);
    if (ok) {
        undoManager.cancelStep();
        compositor.compositeRegion(layerStack.getAllLayersForComposition(), dirtyBounds, outputBuffer, bgColor);
    }
    return ok;
}

bool TransformOrchestrator::flipActiveLayer(
    bool horizontal,
    int width, int height,
    document::LayerStack& layerStack,
    history::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
) {
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) {
        return false;
    }

    utils::Rect2D dirtyBounds;
    bool ok = transformEngineFlipLayer(
        activeLayer, horizontal, width, height, undoManager, layerStack.getActiveIndex(), dirtyBounds
    );
    if (ok) {
        undoManager.commitStep(layerStack);
        compositor.compositeRegion(layerStack.getAllLayersForComposition(), dirtyBounds, outputBuffer, bgColor);
    }
    return ok;
}

bool TransformOrchestrator::rotateActiveLayer90(
    bool clockwise,
    int width, int height,
    document::LayerStack& layerStack,
    history::TileUndoManager& undoManager,
    document::Compositor& compositor,
    canvas::PixelBuffer& outputBuffer,
    const utils::ColorRGBA& bgColor
) {
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) {
        return false;
    }

    utils::Rect2D dirtyBounds;
    bool ok = transformEngineRotateLayer90(
        activeLayer, clockwise, width, height, undoManager, layerStack.getActiveIndex(), dirtyBounds
    );
    if (ok) {
        undoManager.commitStep(layerStack);
        compositor.compositeRegion(layerStack.getAllLayersForComposition(), dirtyBounds, outputBuffer, bgColor);
    }
    return ok;
}

bool TransformOrchestrator::transformEngineFlipLayer(
    document::Layer* activeLayer,
    bool horizontal,
    int canvasWidth,
    int canvasHeight,
    history::TileUndoManager& undoManager,
    int activeLayerIndex,
    utils::Rect2D& outDirtyBounds
) {
    raster::TransformEngine engine;
    return engine.flipLayer(activeLayer, horizontal, canvasWidth, canvasHeight, undoManager, activeLayerIndex, outDirtyBounds);
}

bool TransformOrchestrator::transformEngineRotateLayer90(
    document::Layer* activeLayer,
    bool clockwise,
    int canvasWidth,
    int canvasHeight,
    history::TileUndoManager& undoManager,
    int activeLayerIndex,
    utils::Rect2D& outDirtyBounds
) {
    raster::TransformEngine engine;
    return engine.rotateLayer90(activeLayer, clockwise, canvasWidth, canvasHeight, undoManager, activeLayerIndex, outDirtyBounds);
}

} // namespace aladyn::engine::boundary::orchestrator
