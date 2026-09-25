#ifndef ALADYN_ENGINE_SELECTION_ORCHESTRATOR_HPP
#define ALADYN_ENGINE_SELECTION_ORCHESTRATOR_HPP

#include "../../core/selection/SelectionMask.hpp"
#include "../../core/selection/SelectionEngine.hpp"
#include "../../core/document/LayerStack.hpp"
#include "../../core/history/TileUndoManager.hpp"
#include "../../core/document/Compositor.hpp"
#include <vector>

namespace aladyn::engine::boundary::orchestrator {

class SelectionOrchestrator {
public:
    static bool magicWandSelect(
        int seedX, int seedY, int tolerance, bool contiguous,
        int expandPx, bool antiAliasing, int mode, bool sampleAllLayers,
        int width, int height,
        const canvas::PixelBuffer& outputBuffer,
        const document::LayerStack& layerStack,
        selection::SelectionMask& selectionMask
    );

    static bool selectRect(
        int x, int y, int w, int h, int mode, int featherPx, int cornerRadiusPx,
        int width, int height,
        selection::SelectionMask& selectionMask
    );

    static bool selectEllipse(
        int cx, int cy, int rx, int ry, int mode, bool antiAliasing, int featherPx,
        int width, int height,
        selection::SelectionMask& selectionMask
    );

    static bool selectPolygon(
        const std::vector<int>& flatPoints, int mode, bool antiAliasing, int featherPx,
        int width, int height,
        selection::SelectionMask& selectionMask
    );

    static bool deleteSelectionOnActiveLayer(
        document::LayerStack& layerStack,
        const selection::SelectionMask& selectionMask,
        history::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const utils::ColorRGBA& bgColor
    );

    static bool fillSelectionOnActiveLayer(
        const utils::ColorRGBA& fillColor,
        document::LayerStack& layerStack,
        const selection::SelectionMask& selectionMask,
        history::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const utils::ColorRGBA& bgColor
    );
};

} // namespace aladyn::engine::boundary::orchestrator

#endif // ALADYN_ENGINE_SELECTION_ORCHESTRATOR_HPP
