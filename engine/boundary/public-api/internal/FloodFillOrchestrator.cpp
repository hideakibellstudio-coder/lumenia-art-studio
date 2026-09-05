#include "FloodFillOrchestrator.hpp"
#include "../../../core/raster/FloodFill.hpp"
#include "../../../core/raster/PixelContext.hpp"

namespace aladyn::engine::boundary::internal {

bool FloodFillOrchestrator::floodFill(
    canvas::PixelBuffer& outputBuffer,
    document::LayerStack& layerStack,
    canvas::TileUndoManager& undoManager,
    document::Compositor& compositor,
    const raster::SelectionMask& selectionMask,
    const raster::ColorRGBA& bgColor,
    int seedX, int seedY, const raster::ColorRGBA& fillColor,
    int tolerance, bool contiguous, int expandPx, int gapClosingPx,
    bool antiAliasing, bool /*sampleAllLayers*/
) {
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) return false;

    // Clipping Mask é 100% não-destrutivo: o preenchimento atua no espaço da camada e o recorte é visual
    const raster::PixelContext pCtx{ activeLayer->isAlphaLocked(), nullptr, &selectionMask };

    undoManager.beginStep("Bucket Fill");
    math::Rect2D affectedBounds{0, 0, 0, 0};
    bool ok = raster::FloodFill::execute(
        outputBuffer, seedX, seedY, fillColor, tolerance, contiguous, expandPx, gapClosingPx, antiAliasing,
        activeLayer->getTileGrid(), undoManager, layerStack.getActiveIndex(), pCtx, affectedBounds
    );

    if (ok) {
        undoManager.commitStep(layerStack);
        compositor.compositeRegion(layerStack.getAllLayersForComposition(), affectedBounds, outputBuffer, bgColor);
    }
    return ok;
}

} // namespace aladyn::engine::boundary::internal
