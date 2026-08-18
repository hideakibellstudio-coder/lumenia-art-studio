#include "TileGrid.hpp"
#include <cmath>

namespace aladyn::engine::canvas {

TileGrid::TileGrid(int width, int height)
    : m_width(width), m_height(height) {
    m_tilesX = static_cast<int>(std::ceil(static_cast<double>(width) / Tile::TILE_SIZE));
    m_tilesY = static_cast<int>(std::ceil(static_cast<double>(height) / Tile::TILE_SIZE));
}

Tile* TileGrid::getTile(int tileX, int tileY) {
    const TileIndex idx{tileX, tileY};
    auto it = m_tiles.find(idx);
    if (it != m_tiles.end()) {
        return it->second.get();
    }
    return nullptr;
}

Tile* TileGrid::getOrCreateTile(int tileX, int tileY) {
    if (tileX < 0 || tileX >= m_tilesX || tileY < 0 || tileY >= m_tilesY) {
        return nullptr;
    }
    const TileIndex idx{tileX, tileY};
    auto it = m_tiles.find(idx);
    if (it != m_tiles.end()) {
        return it->second.get();
    }
    auto tile = std::make_unique<Tile>(tileX, tileY);
    Tile* ptr = tile.get();
    m_tiles[idx] = std::move(tile);
    return ptr;
}

void TileGrid::clearAll(raster::ColorRGBA color) {
    for (auto& [idx, tile] : m_tiles) {
        tile->getBuffer().fill(color);
        tile->setDirty(true);
    }
}

void TileGrid::clearTiles() {
    m_tiles.clear();
}

void TileGrid::copyFrom(const TileGrid& src) {
    m_tiles.clear();
    for (const auto& [idx, tile] : src.m_tiles) {
        if (tile) {
            auto dupTile = std::make_unique<Tile>(idx.x, idx.y);
            dupTile->getBuffer() = tile->getBuffer();
            m_tiles[idx] = std::move(dupTile);
        }
    }
}

} // namespace aladyn::engine::canvas
