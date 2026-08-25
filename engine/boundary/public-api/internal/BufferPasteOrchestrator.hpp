#ifndef ALADYN_ENGINE_BUFFER_PASTE_ORCHESTRATOR_HPP
#define ALADYN_ENGINE_BUFFER_PASTE_ORCHESTRATOR_HPP

#include "../../../core/document/LayerStack.hpp"
#include "../../../core/canvas/TileUndoManager.hpp"
#include "../../../core/document/Compositor.hpp"
#include "../../../core/raster/SelectionMask.hpp"

namespace aladyn::engine::boundary::internal {

class BufferPasteOrchestrator {
public:
    static bool paste(
        int x, int y, int width, int height,
        const uint8_t* buffer,
        int blendModeId, double opacity,
        int canvasWidth, int canvasHeight,
        document::LayerStack& layerStack,
        const raster::SelectionMask& selectionMask,
        canvas::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const raster::ColorRGBA& bgColor
    );
};

} // namespace aladyn::engine::boundary::internal

#endif // ALADYN_ENGINE_BUFFER_PASTE_ORCHESTRATOR_HPP
