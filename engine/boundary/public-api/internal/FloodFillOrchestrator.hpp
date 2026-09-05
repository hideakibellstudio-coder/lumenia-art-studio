#ifndef ALADYN_ENGINE_FLOOD_FILL_ORCHESTRATOR_HPP
#define ALADYN_ENGINE_FLOOD_FILL_ORCHESTRATOR_HPP

#include "../../../core/canvas/PixelBuffer.hpp"
#include "../../../core/document/LayerStack.hpp"
#include "../../../core/canvas/TileUndoManager.hpp"
#include "../../../core/document/Compositor.hpp"
#include "../../../core/raster/SelectionMask.hpp"
#include "../../../core/raster/Dab.hpp"

namespace aladyn::engine::boundary::internal {

class FloodFillOrchestrator {
public:
    static bool floodFill(
        canvas::PixelBuffer& outputBuffer,
        document::LayerStack& layerStack,
        canvas::TileUndoManager& undoManager,
        document::Compositor& compositor,
        const raster::SelectionMask& selectionMask,
        const raster::ColorRGBA& bgColor,
        int seedX, int seedY, const raster::ColorRGBA& fillColor,
        int tolerance, bool contiguous, int expandPx, int gapClosingPx,
        bool antiAliasing, bool sampleAllLayers
    );
};

} // namespace aladyn::engine::boundary::internal

#endif // ALADYN_ENGINE_FLOOD_FILL_ORCHESTRATOR_HPP
