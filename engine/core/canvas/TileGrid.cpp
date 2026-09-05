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

size_t TileGrid::pruneEmptyTiles() {
    size_t pruned = 0;
    auto it = m_tiles.begin();
    while (it != m_tiles.end()) {
        if (it->second && it->second->isEmpty()) {
            it = m_tiles.erase(it);
            ++pruned;
        } else {
            ++it;
        }
    }
    return pruned;
}

void TileGrid::copyFrom(const TileGrid& src) {
    m_tiles.clear();
    for (const auto& [idx, tile] : src.m_tiles) {
        if (tile) {
            // Copy-on-Write (COW): compartilha o buffer com zero alocação de 64KB!
            auto dupTile = std::make_unique<Tile>(idx.x, idx.y, tile->getSharedBuffer());
            dupTile->setDirty(tile->isDirty());
            m_tiles[idx] = std::move(dupTile);
        }
    }
}

size_t TileGrid::compressInactiveTiles() {
    size_t count = 0;
    for (auto& [idx, tile] : m_tiles) {
        if (tile && !tile->isCompressed()) {
            if (tile->compress()) {
                ++count;
            }
        }
    }
    return count;
}

size_t TileGrid::decompressAllTiles() {
    size_t count = 0;
    for (auto& [idx, tile] : m_tiles) {
        if (tile && tile->isCompressed()) {
            if (tile->decompress()) {
                ++count;
            }
        }
    }
    return count;
}

size_t TileGrid::getMemoryFootprintBytes() const noexcept {
    size_t total = sizeof(TileGrid) + (m_tiles.size() * (sizeof(TileIndex) + sizeof(std::unique_ptr<Tile>)));
    for (const auto& [idx, tile] : m_tiles) {
        if (tile) {
            total += tile->getMemoryFootprint();
        }
    }
    return total;
}

size_t TileGrid::getCompressedTilesCount() const noexcept {
    size_t count = 0;
    for (const auto& [idx, tile] : m_tiles) {
        if (tile && tile->isCompressed()) ++count;
    }
    return count;
}

size_t TileGrid::getCowSharedTilesCount() const noexcept {
    size_t count = 0;
    for (const auto& [idx, tile] : m_tiles) {
        if (tile && tile->isShared()) ++count;
    }
    return count;
}

} // namespace aladyn::engine::canvas
