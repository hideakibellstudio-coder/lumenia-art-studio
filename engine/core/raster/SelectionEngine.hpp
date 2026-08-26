#ifndef ALADYN_ENGINE_SELECTION_ENGINE_HPP
#define ALADYN_ENGINE_SELECTION_ENGINE_HPP

#include "SelectionMask.hpp"
#include "../canvas/PixelBuffer.hpp"
#include <vector>

namespace aladyn::engine::raster {

class SelectionEngine {
public:
    static std::vector<uint8_t> generateWandMask(
        const canvas::PixelBuffer& sourceBuffer,
        int seedX,
        int seedY,
        int tolerance,
        bool contiguous,
        int expandPx,
        bool antiAliasing
    );

    static std::vector<uint8_t> generateRectMask(
        int width,
        int height,
        int x,
        int y,
        int w,
        int h,
        int featherPx = 0,
        int cornerRadiusPx = 0
    );

    static std::vector<uint8_t> generateEllipseMask(
        int width,
        int height,
        int cx,
        int cy,
        int rx,
        int ry,
        bool antiAliasing = true,
        int featherPx = 0
    );

    static std::vector<uint8_t> generatePolygonMask(
        int width,
        int height,
        const std::vector<std::pair<int, int>>& points,
        bool antiAliasing = true,
        int featherPx = 0
    );

    static void applyFeather(
        std::vector<uint8_t>& mask,
        int width,
        int height,
        int featherPx
    );
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_SELECTION_ENGINE_HPP
