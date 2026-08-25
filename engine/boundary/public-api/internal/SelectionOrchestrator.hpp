#ifndef ALADYN_ENGINE_SELECTION_ORCHESTRATOR_HPP
#define ALADYN_ENGINE_SELECTION_ORCHESTRATOR_HPP

#include "../../../core/raster/SelectionMask.hpp"
#include "../../../core/raster/SelectionEngine.hpp"
#include "../../../core/document/LayerStack.hpp"
#include "../../../core/canvas/TileUndoManager.hpp"
#include "../../../core/document/Compositor.hpp"
#include <vector>

namespace aladyn::engine::boundary::internal {

class SelectionOrchestrator {
public:
    static bool magicWandSelect(
        int seedX, int seedY, int tolerance, bool contiguous,
        int expandPx, bool antiAliasing, int mode, bool sampleAllLayers,
        int width, int height,
        const canvas::PixelBuffer& outputBuffer,
        const document::LayerStack& layerStack,
        raster::SelectionMask& selectionMask
    );

    static bool selectRect(
        int x, int y, int w, int h, int mode, int featherPx, int cornerRadiusPx,
        int width, int height,
        raster::SelectionMask& selectionMask
    );

    static bool selectEllipse(
        int cx, int cy, int rx, int ry, int mode, bool antiAliasing, int featherPx,
        int width, int height,
        raster::SelectionMask& selectionMask
    );

    static bool selectPolygon(
        const std::vector<int>& flatPoints, int mode, bool antiAliasing, int featherPx,
        int width, int height,
        raster::SelectionMask& selectionMask
    );

    static bool deleteSelectionOnActiveLayer(
        document::LayerStack& layerStack,
        const raster::SelectionMask& selectionMask,
        canvas::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const raster::ColorRGBA& bgColor
    );

    static bool fillSelectionOnActiveLayer(
        const raster::ColorRGBA& fillColor,
        document::LayerStack& layerStack,
        const raster::SelectionMask& selectionMask,
        canvas::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const raster::ColorRGBA& bgColor
    );
};

} // namespace aladyn::engine::boundary::internal

#endif // ALADYN_ENGINE_SELECTION_ORCHESTRATOR_HPP
