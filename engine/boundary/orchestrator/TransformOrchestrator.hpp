#ifndef ALADYN_ENGINE_TRANSFORM_ORCHESTRATOR_HPP
#define ALADYN_ENGINE_TRANSFORM_ORCHESTRATOR_HPP

#include "../../core/raster/TransformEngine.hpp"
#include "../../core/selection/SelectionMask.hpp"
#include "../../core/document/LayerStack.hpp"
#include "../../core/history/TileUndoManager.hpp"
#include "../../core/document/Compositor.hpp"
#include <array>
#include <vector>

namespace aladyn::engine::boundary::orchestrator {

class TransformOrchestrator {
public:
    static bool beginTransform(
        raster::TransformEngine& transformEngine,
        document::LayerStack& layerStack,
        const selection::SelectionMask& selectionMask,
        history::TileUndoManager& undoManager,
        int canvasWidth, int canvasHeight
    );

    static bool commitTransform(
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
    );

    /// Distorcer. Quad inválido (não convexo / fora da tela) cancela a
    /// transformação -- os pixels voltam ao lugar -- e devolve false.
    static bool commitTransformDistort(
        raster::TransformEngine& transformEngine,
        document::LayerStack& layerStack,
        history::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const utils::ColorRGBA& bgColor,
        const std::array<double, 8>& corners, int interpMode,
        int canvasWidth, int canvasHeight
    );

    static bool cancelTransform(
        raster::TransformEngine& transformEngine,
        document::LayerStack& layerStack,
        history::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const utils::ColorRGBA& bgColor
    );

    static bool flipActiveLayer(
        bool horizontal,
        int width, int height,
        document::LayerStack& layerStack,
        history::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const utils::ColorRGBA& bgColor
    );

    static bool rotateActiveLayer90(
        bool clockwise,
        int width, int height,
        document::LayerStack& layerStack,
        history::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const utils::ColorRGBA& bgColor
    );

private:
    static bool transformEngineFlipLayer(
        document::Layer* activeLayer,
        bool horizontal,
        int canvasWidth,
        int canvasHeight,
        history::TileUndoManager& undoManager,
        int activeLayerIndex,
        utils::Rect2D& outDirtyBounds
    );

    static bool transformEngineRotateLayer90(
        document::Layer* activeLayer,
        bool clockwise,
        int canvasWidth,
        int canvasHeight,
        history::TileUndoManager& undoManager,
        int activeLayerIndex,
        utils::Rect2D& outDirtyBounds
    );
};

} // namespace aladyn::engine::boundary::orchestrator

#endif // ALADYN_ENGINE_TRANSFORM_ORCHESTRATOR_HPP
