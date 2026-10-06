#include "DabFootprint.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../../utils/Rect2D.hpp"

namespace aladyn::engine::raster {

DabFootprint::DabFootprint(const utils::Dab& dab, double reach, double aspect, canvas::TileGrid& grid)
    : m_center(dab.position), m_format(grid.getFormat()) {
    // A caixa envolvente cobre a ponta achatada e girada; o raio máximo, a elipse inteira.
    const double maxR = reach / aspect + 2.0;
    m_bounds = utils::Rect2D{dab.position.x - maxR, dab.position.y - maxR, maxR * 2.0, maxR * 2.0};
    const double maxRadius = reach + 1.0;
    m_maxRadiusSq = maxRadius * maxRadius;

    m_circular = (aspect >= 0.999) && (std::abs(dab.angle) < 0.001);
    if (!m_circular) {
        const double radAngle = -dab.angle * (3.14159265358979323846 / 180.0);
        m_cosA = std::cos(radAngle);
        m_sinA = std::sin(radAngle);
        m_invAspect = 1.0 / aspect;
    }

    // Descarta o tile cujo ponto mais próximo do centro está além do círculo da caixa, sem alocá-lo.
    const double maxRSq = maxR * maxR;
    const auto candidates = canvas::SpatialCuller::getIntersectingTiles(m_bounds, grid.getWidth(), grid.getHeight());
    m_tiles.reserve(candidates.size());
    for (const auto& index : candidates) {
        const double tileX0 = static_cast<double>(index.x * canvas::Tile::TILE_SIZE);
        const double tileY0 = static_cast<double>(index.y * canvas::Tile::TILE_SIZE);
        const double nearestX = std::clamp(dab.position.x, tileX0, tileX0 + canvas::Tile::TILE_SIZE);
        const double nearestY = std::clamp(dab.position.y, tileY0, tileY0 + canvas::Tile::TILE_SIZE);
        const double dx = dab.position.x - nearestX;
        const double dy = dab.position.y - nearestY;
        if (dx * dx + dy * dy > maxRSq) continue;

        if (canvas::Tile* tile = grid.getOrCreateTile(index.x, index.y)) m_tiles.push_back(tile);
    }
}

} // namespace aladyn::engine::raster
