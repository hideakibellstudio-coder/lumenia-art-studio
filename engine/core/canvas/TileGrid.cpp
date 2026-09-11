#include "TileGrid.hpp"
#include <cmath>
#include <algorithm>
#include <cstring>

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

void TileGrid::resizePreserve(int width, int height, int offsetX, int offsetY) {
    width = std::max(1, width);
    height = std::max(1, height);
    if (width == m_width && height == m_height && offsetX == 0 && offsetY == 0) {
        return;
    }

    // Move a grade antiga para preservar todos os tiles sem perder metadados da
    // camada. A operação ocorre fora do caminho de pintura e pode ser mais lenta.
    TileGrid old = std::move(*this);
    m_width = width;
    m_height = height;
    m_tilesX = static_cast<int>(std::ceil(static_cast<double>(width) / Tile::TILE_SIZE));
    m_tilesY = static_cast<int>(std::ceil(static_cast<double>(height) / Tile::TILE_SIZE));
    m_tiles.clear();

    for (const auto& [idx, sourceTile] : old.m_tiles) {
        if (!sourceTile) continue;
        const PixelBuffer& src = sourceTile->getBuffer();
        const int srcBaseX = sourceTile->getPixelX() + offsetX;
        const int srcBaseY = sourceTile->getPixelY() + offsetY;

        const int minX = std::max(0, srcBaseX);
        const int minY = std::max(0, srcBaseY);
        const int maxX = std::min(width, srcBaseX + Tile::TILE_SIZE);
        const int maxY = std::min(height, srcBaseY + Tile::TILE_SIZE);
        if (minX >= maxX || minY >= maxY) continue;

        const auto* srcData = reinterpret_cast<const uint8_t*>(src.getData());
        for (int y = minY; y < maxY; ++y) {
            const int localY = y - srcBaseY;
            for (int x = minX; x < maxX; ++x) {
                const int localX = x - srcBaseX;
                const size_t srcOffset = static_cast<size_t>(localY * Tile::TILE_SIZE + localX) * 4u;
                // Não aloca tiles para pixels transparentes durante expansão.
                if (srcData[srcOffset + 3] == 0 && srcData[srcOffset] == 0 &&
                    srcData[srcOffset + 1] == 0 && srcData[srcOffset + 2] == 0) {
                    continue;
                }
                Tile* destinationTile = getOrCreateTile(x / Tile::TILE_SIZE, y / Tile::TILE_SIZE);
                if (!destinationTile) continue;
                auto* dstData = reinterpret_cast<uint8_t*>(destinationTile->getBuffer().getData());
                const int dstLocalX = x % Tile::TILE_SIZE;
                const int dstLocalY = y % Tile::TILE_SIZE;
                const size_t dstOffset = static_cast<size_t>(dstLocalY * Tile::TILE_SIZE + dstLocalX) * 4u;
                std::memcpy(dstData + dstOffset, srcData + srcOffset, 4u);
                destinationTile->setDirty(true);
            }
        }
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

std::vector<std::pair<int, int>> TileGrid::getDirtyTileIndices() const {
    std::vector<std::pair<int, int>> dirty;
    for (const auto& [idx, tile] : m_tiles) {
        if (tile && tile->isDirty()) {
            dirty.emplace_back(idx.x, idx.y);
        }
    }
    return dirty;
}

void TileGrid::clearDirtyFlags() noexcept {
    for (auto& [idx, tile] : m_tiles) {
        if (tile) tile->setDirty(false);
    }
}

const uint8_t* TileGrid::getTileData(int tileX, int tileY) const noexcept {
    const TileIndex idx{tileX, tileY};
    auto it = m_tiles.find(idx);
    if (it != m_tiles.end() && it->second) {
        return it->second->getBuffer().getData();
    }
    return nullptr;
}

size_t TileGrid::getTileDataSize() const noexcept {
    return Tile::TILE_BYTES;
}

} // namespace aladyn::engine::canvas
