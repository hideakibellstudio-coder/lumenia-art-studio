#ifndef ALADYN_ENGINE_FLOOD_FILL_ORCHESTRATOR_HPP
#define ALADYN_ENGINE_FLOOD_FILL_ORCHESTRATOR_HPP

#include "../../core/canvas/PixelBuffer.hpp"
#include "../../core/document/LayerStack.hpp"
#include "../../core/history/TileUndoManager.hpp"
#include "../../core/document/Compositor.hpp"
#include "../../core/selection/SelectionMask.hpp"
#include "../../utils/ColorRGBA.hpp"

namespace aladyn::engine::boundary::orchestrator {

class FloodFillOrchestrator {
public:
    static bool floodFill(
        canvas::PixelBuffer& outputBuffer,
        document::LayerStack& layerStack,
        history::TileUndoManager& undoManager,
        document::Compositor& compositor,
        const selection::SelectionMask& selectionMask,
        const utils::ColorRGBA& bgColor,
        int seedX, int seedY, const utils::ColorRGBA& fillColor,
        int tolerance, bool contiguous, int expandPx, bool sampleAllLayers
    );
};

} // namespace aladyn::engine::boundary::orchestrator

#endif // ALADYN_ENGINE_FLOOD_FILL_ORCHESTRATOR_HPP
