#ifndef ALADYN_ENGINE_TRANSFORM_ORCHESTRATOR_HPP
#define ALADYN_ENGINE_TRANSFORM_ORCHESTRATOR_HPP

#include "../../../core/raster/TransformEngine.hpp"
#include "../../../core/raster/SelectionMask.hpp"
#include "../../../core/document/LayerStack.hpp"
#include "../../../core/canvas/TileUndoManager.hpp"
#include "../../../core/document/Compositor.hpp"
#include <array>
#include <vector>

namespace aladyn::engine::boundary::internal {

class TransformOrchestrator {
public:
    static bool beginTransform(
        raster::TransformEngine& transformEngine,
        document::LayerStack& layerStack,
        const raster::SelectionMask& selectionMask,
        canvas::TileUndoManager& undoManager,
        int canvasWidth, int canvasHeight
    );

    static bool commitTransform(
        raster::TransformEngine& transformEngine,
        document::LayerStack& layerStack,
        canvas::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const raster::ColorRGBA& bgColor,
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
        canvas::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const raster::ColorRGBA& bgColor,
        const std::array<double, 8>& corners, int interpMode,
        int canvasWidth, int canvasHeight
    );

    static bool cancelTransform(
        raster::TransformEngine& transformEngine,
        document::LayerStack& layerStack,
        canvas::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const raster::ColorRGBA& bgColor,
        int canvasWidth, int canvasHeight
    );

    static bool flipActiveLayer(
        bool horizontal,
        int width, int height,
        document::LayerStack& layerStack,
        canvas::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const raster::ColorRGBA& bgColor
    );

    static bool rotateActiveLayer90(
        bool clockwise,
        int width, int height,
        document::LayerStack& layerStack,
        canvas::TileUndoManager& undoManager,
        document::Compositor& compositor,
        canvas::PixelBuffer& outputBuffer,
        const raster::ColorRGBA& bgColor
    );

private:
    static bool transformEngineFlipLayer(
        document::Layer* activeLayer,
        bool horizontal,
        int canvasWidth,
        int canvasHeight,
        canvas::TileUndoManager& undoManager,
        int activeLayerIndex,
        math::Rect2D& outDirtyBounds
    );

    static bool transformEngineRotateLayer90(
        document::Layer* activeLayer,
        bool clockwise,
        int canvasWidth,
        int canvasHeight,
        canvas::TileUndoManager& undoManager,
        int activeLayerIndex,
        math::Rect2D& outDirtyBounds
    );
};

} // namespace aladyn::engine::boundary::internal

#endif // ALADYN_ENGINE_TRANSFORM_ORCHESTRATOR_HPP
