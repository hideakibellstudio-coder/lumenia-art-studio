#include "FloodFillOrchestrator.hpp"
#include "LayerSampleSource.hpp"
#include "PixelFormatGuard.hpp"
#include "../../core/raster/FloodFill.hpp"
#include "../../core/raster/PixelContext.hpp"

namespace aladyn::engine::boundary::orchestrator {

bool FloodFillOrchestrator::floodFill(
    canvas::PixelBuffer& outputBuffer,
    document::LayerStack& layerStack,
    history::TileUndoManager& undoManager,
    document::Compositor& compositor,
    const selection::SelectionMask& selectionMask,
    const utils::ColorRGBA& bgColor,
    int seedX, int seedY, const utils::ColorRGBA& fillColor,
    int tolerance, bool contiguous, int expandPx, bool sampleAllLayers
) {
    document::Layer* activeLayer = layerStack.getActiveLayer();
    if (!activeLayer || activeLayer->isLocked() || activeLayer->isGroup() || activeLayer->isFilter()) return false;

    // Clipping Mask é 100% não-destrutivo: o preenchimento atua no espaço da camada e o recorte é visual
    const raster::PixelContext pCtx{ activeLayer->isAlphaLocked(), nullptr, &selectionMask };
    std::unique_ptr<canvas::PixelBuffer> activeLayerPixels;
    // O balde sobre todas as camadas lê as cores da composição, que pode ter tiles velhos.
    if (sampleAllLayers) compositor.ensureAllFresh(layerStack.getAllLayersForComposition(), outputBuffer, bgColor);
    const canvas::PixelBuffer* source =
        LayerSampleSource::select(sampleAllLayers, outputBuffer, layerStack, activeLayerPixels);
    if (!source) return false;

    undoManager.beginStep("Bucket Fill");
    utils::Rect2D affectedBounds{0, 0, 0, 0};
    bool ok = raster::FloodFill::execute(
        *source, seedX, seedY, fillColor, tolerance, contiguous, expandPx,
        activeLayer->getTileGrid(), undoManager, layerStack.getActiveIndex(), pCtx, affectedBounds
    );

    if (ok) {
        undoManager.commitStep(layerStack);
        compositor.compositeRegion(layerStack.getAllLayersForComposition(), affectedBounds, outputBuffer, bgColor);
    }
    return ok;
}

} // namespace aladyn::engine::boundary::orchestrator
