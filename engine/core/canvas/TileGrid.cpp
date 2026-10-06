#include "TileGrid.hpp"
#include <cmath>
#include <algorithm>
#include <cstring>

namespace aladyn::engine::canvas {

TileGrid::TileGrid(int width, int height, PixelFormat format)
    : m_width(width), m_height(height), m_format(format) {
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

namespace {
constexpr int kMaxTileCoord = 32767;

inline int divFloor(int a, int b) noexcept {
    int res = a / b;
    int rem = a % b;
    if (rem != 0 && ((a < 0) ^ (b < 0))) {
        --res;
    }
    return res;
}
} // namespace

Tile* TileGrid::getOrCreateTile(int tileX, int tileY) {
    if (tileX < -kMaxTileCoord || tileX > kMaxTileCoord || tileY < -kMaxTileCoord || tileY > kMaxTileCoord) {
        return nullptr;
    }
    const TileIndex idx{tileX, tileY};
    auto it = m_tiles.find(idx);
    if (it != m_tiles.end()) {
        return it->second.get();
    }
    auto tile = std::make_unique<Tile>(tileX, tileY, m_format);
    Tile* ptr = tile.get();
    m_tiles[idx] = std::move(tile);
    return ptr;
}

Tile* TileGrid::adoptTile(int tileX, int tileY, std::shared_ptr<PixelBuffer> buffer) {
    if (tileX < -kMaxTileCoord || tileX > kMaxTileCoord || tileY < -kMaxTileCoord || tileY > kMaxTileCoord) return nullptr;
    if (!buffer || buffer->getFormat() != m_format) return nullptr;
    auto tile = std::make_unique<Tile>(tileX, tileY, std::move(buffer));
    Tile* ptr = tile.get();
    m_tiles[TileIndex{tileX, tileY}] = std::move(tile);
    return ptr;
}

void TileGrid::clearAll(utils::ColorRGBA color) {
    for (auto& [idx, tile] : m_tiles) {
        tile->getBuffer().fill(color);
        tile->setDirty(true);
    }
}

namespace {

constexpr int kTile = Tile::TILE_SIZE;

// O bloco [x0, x1) x [y0, y1) do tile `data` (de `pixelBytes` bytes por pixel) é só transparente-preto (todos os
// canais em 0)? Um pixel de alfa 0 que ainda tem cor NÃO é: é o que a borracha deixa, e a redimensão o preserva.
bool blockIsAllZero(const uint8_t* data, size_t pixelBytes, int x0, int x1, int y0, int y1) noexcept {
    const uint8_t* zeros = zeroTileData();
    const size_t rowBytes = static_cast<size_t>(x1 - x0) * pixelBytes;
    for (int y = y0; y < y1; ++y) {
        if (std::memcmp(data + (static_cast<size_t>(y) * kTile + static_cast<size_t>(x0)) * pixelBytes, zeros, rowBytes) != 0) {
            return false;
        }
    }
    return true;
}

} // namespace

void TileGrid::resizePreserve(int width, int height, int offsetX, int offsetY) {
    width = std::max(1, width);
    height = std::max(1, height);
    if (width == m_width && height == m_height && offsetX == 0 && offsetY == 0) {
        return;
    }

    // Move a grade antiga para preservar todos os tiles sem perder metadados da
    // camada. A operação ocorre fora do caminho de pintura.
    TileGrid old = std::move(*this);
    m_width = width;
    m_height = height;
    m_tilesX = static_cast<int>(std::ceil(static_cast<double>(width) / Tile::TILE_SIZE));
    m_tilesY = static_cast<int>(std::ceil(static_cast<double>(height) / Tile::TILE_SIZE));
    m_tiles.clear();

    if (offsetX == 0 && offsetY == 0) {
        m_tiles = std::move(old.m_tiles);
        for (auto& [idx, sourceTile] : m_tiles) {
            if (sourceTile) sourceTile->setDirty(true);
        }
        return;
    }

    const size_t pixelBytes = bytesPerPixel(m_format);
    PixelBuffer scratch(kTile, kTile, m_format, utils::ColorRGBA{0, 0, 0, 0});
    for (auto& [idx, sourceTile] : old.m_tiles) {
        if (!sourceTile) continue;
        const int srcBaseX = sourceTile->getPixelX() + offsetX;
        const int srcBaseY = sourceTile->getPixelY() + offsetY;

        const int minX = srcBaseX;
        const int minY = srcBaseY;
        const int maxX = srcBaseX + kTile;
        const int maxY = srcBaseY + kTile;

        const uint8_t* srcData = sourceTile->view(scratch).getData();
        for (int destTileY = divFloor(minY, kTile); destTileY <= divFloor(maxY - 1, kTile); ++destTileY) {
            for (int destTileX = divFloor(minX, kTile); destTileX <= divFloor(maxX - 1, kTile); ++destTileX) {
                const int x0 = std::max(minX, destTileX * kTile), x1 = std::min(maxX, (destTileX + 1) * kTile);
                const int y0 = std::max(minY, destTileY * kTile), y1 = std::min(maxY, (destTileY + 1) * kTile);
                if (blockIsAllZero(srcData, pixelBytes, x0 - srcBaseX, x1 - srcBaseX, y0 - srcBaseY, y1 - srcBaseY)) continue;
                Tile* destinationTile = getOrCreateTile(destTileX, destTileY);
                if (!destinationTile) continue;
                uint8_t* dstData = destinationTile->getBuffer().getData();
                const size_t rowBytes = static_cast<size_t>(x1 - x0) * pixelBytes;
                for (int y = y0; y < y1; ++y) {
                    const size_t srcOffset = (static_cast<size_t>(y - srcBaseY) * kTile + static_cast<size_t>(x0 - srcBaseX)) * pixelBytes;
                    const size_t dstOffset = (static_cast<size_t>(y - destTileY * kTile) * kTile + static_cast<size_t>(x0 - destTileX * kTile)) * pixelBytes;
                    std::memcpy(dstData + dstOffset, srcData + srcOffset, rowBytes);
                }
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
    m_format = src.m_format;
    for (const auto& [idx, tile] : src.m_tiles) {
        if (tile) {
            // Um tile comprimido não tem buffer para compartilhar (o buffer foi liberado):
            // sem descomprimir antes, a cópia saía em branco, em silêncio.
            tile->ensureDecompressed();
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
    return Tile::bytesFor(m_format);
}

} // namespace aladyn::engine::canvas
