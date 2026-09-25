#ifndef ALADYN_ENGINE_BUFFER_PASTE_ORCHESTRATOR_HPP
#define ALADYN_ENGINE_BUFFER_PASTE_ORCHESTRATOR_HPP

#include "../../core/document/LayerStack.hpp"
#include "../../core/history/TileUndoManager.hpp"
#include "../../core/document/Compositor.hpp"
#include "../../core/selection/SelectionMask.hpp"

namespace aladyn::engine::boundary::orchestrator {

class BufferPasteOrchestrator {
public:
    static bool paste(
        int x, int y, int width, int height,
        const uint8_t* buffer,
        int blendModeId, double opacity,
        int canvasWidth, int canvasHeight,
        document::LayerStack& layerStack,
        const selection::SelectionMask& selectionMask,
        history::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const utils::ColorRGBA& bgColor
    );
};

} // namespace aladyn::engine::boundary::orchestrator

#endif // ALADYN_ENGINE_BUFFER_PASTE_ORCHESTRATOR_HPP
