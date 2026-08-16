#ifndef ALADYN_ENGINE_SPATIAL_CULLER_HPP
#define ALADYN_ENGINE_SPATIAL_CULLER_HPP

#include "../math/Rect2D.hpp"
#include "Tile.hpp"
#include <vector>
#include <utility>

namespace aladyn::engine::canvas {

struct TileIndex {
    int x{0};
    int y{0};

    constexpr bool operator==(const TileIndex& other) const noexcept {
        return x == other.x && y == other.y;
    }
};

class SpatialCuller {
public:
    static std::vector<TileIndex> getIntersectingTiles(
        const math::Rect2D& boundingBox,
        int documentWidth,
        int documentHeight
    );
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_SPATIAL_CULLER_HPP
