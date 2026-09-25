#ifndef ALADYN_ENGINE_FLOOD_FILL_HPP
#define ALADYN_ENGINE_FLOOD_FILL_HPP

#include "../../utils/ColorRGBA.hpp"
#include "PixelContext.hpp"
#include "../canvas/PixelBuffer.hpp"
#include "../canvas/TileGrid.hpp"
#include "../history/TileUndoManager.hpp"
#include "../../utils/Rect2D.hpp"
#include <vector>
#include <cstdint>

namespace aladyn::engine::raster {

class FloodFill {
public:
    static bool execute(
        const canvas::PixelBuffer& sourceBuffer,
        int seedX,
        int seedY,
        const utils::ColorRGBA& fillColor,
        int tolerance,
        bool contiguous,
        int expandPx,
        canvas::TileGrid& targetGrid,
        history::TileUndoManager& undoManager,
        int activeLayerIndex,
        const PixelContext& pCtx,
        utils::Rect2D& outAffectedBounds
    );
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_FLOOD_FILL_HPP
