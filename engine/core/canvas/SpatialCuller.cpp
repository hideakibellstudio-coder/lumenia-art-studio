#include "SpatialCuller.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::canvas {

std::vector<TileIndex> SpatialCuller::getIntersectingTiles(
    const math::Rect2D& boundingBox,
    int documentWidth,
    int documentHeight
) {
    std::vector<TileIndex> result;

    const double left = std::max(0.0, boundingBox.getLeft());
    const double top = std::max(0.0, boundingBox.getTop());
    const double right = std::min(static_cast<double>(documentWidth), boundingBox.getRight());
    const double bottom = std::min(static_cast<double>(documentHeight), boundingBox.getBottom());

    if (left >= right || top >= bottom) {
        return result;
    }

    const int minTileX = static_cast<int>(std::floor(left / Tile::TILE_SIZE));
    const int maxTileX = static_cast<int>(std::floor((right - 1.0) / Tile::TILE_SIZE));
    const int minTileY = static_cast<int>(std::floor(top / Tile::TILE_SIZE));
    const int maxTileY = static_cast<int>(std::floor((bottom - 1.0) / Tile::TILE_SIZE));

    for (int ty = minTileY; ty <= maxTileY; ++ty) {
        for (int tx = minTileX; tx <= maxTileX; ++tx) {
            result.push_back(TileIndex{tx, ty});
        }
    }

    return result;
}

} // namespace aladyn::engine::canvas
