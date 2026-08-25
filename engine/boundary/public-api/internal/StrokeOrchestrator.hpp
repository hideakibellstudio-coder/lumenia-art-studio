#ifndef ALADYN_ENGINE_STROKE_ORCHESTRATOR_HPP
#define ALADYN_ENGINE_STROKE_ORCHESTRATOR_HPP

#include "../../../core/raster/Dab.hpp"
#include "../../../core/brush/BrushProfile.hpp"
#include "../../../core/canvas/CanvasTexture.hpp"
#include "../../../core/document/LayerStack.hpp"
#include "../../../core/canvas/TileUndoManager.hpp"
#include "../../../core/document/Compositor.hpp"
#include "../../../core/raster/SelectionMask.hpp"
#include "../../../core/engines/IBrushEngine.hpp"
#include "../../../core/math/SymmetryEngine.hpp"

namespace aladyn::engine::boundary::internal {

class StrokeOrchestrator {
public:
    static void renderSegment(
        const raster::Dab& startDab,
        const raster::Dab& endDab,
        const brush::BrushProfile& brushProfile,
        const canvas::CanvasTexture& canvasTexture,
        engines::IBrushEngine* activeEngine,
        document::LayerStack& layerStack,
        const raster::SelectionMask& selectionMask,
        canvas::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const raster::ColorRGBA& bgColor,
        double& distanceCarryover,
        const math::SymmetryConfig& symmetryConfig = {},
        const math::Point2D* strokeStart = nullptr
    );
};

} // namespace aladyn::engine::boundary::internal

#endif // ALADYN_ENGINE_STROKE_ORCHESTRATOR_HPP
