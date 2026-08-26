#ifndef ALADYN_ENGINE_FLOOD_FILL_HPP
#define ALADYN_ENGINE_FLOOD_FILL_HPP

#include "Dab.hpp"
#include "PixelContext.hpp"
#include "../canvas/PixelBuffer.hpp"
#include "../canvas/TileGrid.hpp"
#include "../canvas/TileUndoManager.hpp"
#include "../math/Rect2D.hpp"
#include <vector>
#include <cstdint>

namespace aladyn::engine::raster {

class FloodFill {
public:
    static bool execute(
        const canvas::PixelBuffer& sourceBuffer,
        int seedX,
        int seedY,
        const ColorRGBA& fillColor,
        int tolerance,
        bool contiguous,
        int expandPx,
        int gapClosingPx,
        bool antiAliasing,
        canvas::TileGrid& targetGrid,
        canvas::TileUndoManager& undoManager,
        int activeLayerIndex,
        const PixelContext& pCtx,
        math::Rect2D& outAffectedBounds
    );
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_FLOOD_FILL_HPP
