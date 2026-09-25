#include "Tile.hpp"
#include "../../infrastructure/compression/Lz4Codec.hpp"
#include <algorithm>

namespace aladyn::engine::canvas {

Tile::Tile(int tileX, int tileY)
    : m_tileX(tileX), m_tileY(tileY),
      m_buffer(std::make_shared<PixelBuffer>(TILE_SIZE, TILE_SIZE, utils::ColorRGBA{0, 0, 0, 0})) {}

Tile::Tile(int tileX, int tileY, std::shared_ptr<PixelBuffer> sharedBuffer)
    : m_tileX(tileX), m_tileY(tileY), m_buffer(std::move(sharedBuffer)) {
    if (!m_buffer) {
        m_buffer = std::make_shared<PixelBuffer>(TILE_SIZE, TILE_SIZE, utils::ColorRGBA{0, 0, 0, 0});
    }
}

PixelBuffer& Tile::getBuffer() noexcept {
    ensureDecompressed();
    ensureUnique();
    return *m_buffer;
}

const PixelBuffer& Tile::getBuffer() const noexcept {
    ensureDecompressed();
    return *m_buffer;
}

void Tile::ensureDecompressed() const noexcept {
    if (m_isCompressed) {
        const_cast<Tile*>(this)->decompress();
    }
}

void Tile::ensureUnique() {
    if (m_buffer && m_buffer.use_count() > 1) {
        m_buffer = std::make_shared<PixelBuffer>(*m_buffer);
    }
}

bool Tile::compress() noexcept {
    if (m_isCompressed) return true;
    if (!m_buffer) return false;

    // Se o buffer for compartilhado por COW com outro tile, não comprime inline
    if (m_buffer.use_count() > 1) {
        return false;
    }

    const uint8_t* rawData = m_buffer->getData();
    const size_t rawSize = m_buffer->getSizeInBytes();

    std::vector<uint8_t> compressed = compression::Lz4Codec::compress(rawData, rawSize);
    if (compressed.empty()) return false;

    m_compressedData = std::move(compressed);
    m_compressedData.shrink_to_fit();
    m_buffer.reset();
    m_isCompressed = true;
    return true;
}

bool Tile::decompress() noexcept {
    if (!m_isCompressed) return true;
    if (m_compressedData.empty()) return false;

    auto newBuf = std::make_shared<PixelBuffer>(TILE_SIZE, TILE_SIZE, utils::ColorRGBA{0, 0, 0, 0});
    bool ok = compression::Lz4Codec::decompressBlock(
        m_compressedData.data(),
        m_compressedData.size(),
        newBuf->getData(),
        TILE_BYTES
    );
    if (!ok) return false;

    m_buffer = std::move(newBuf);
    m_compressedData.clear();
    m_compressedData.shrink_to_fit();
    m_isCompressed = false;
    return true;
}

bool Tile::isEmpty() const noexcept {
    const PixelBuffer& buf = getBuffer();
    const uint8_t* ptr = buf.getData();
    const size_t sz = buf.getSizeInBytes();
    for (size_t i = 3; i < sz; i += 4) {
        if (ptr[i] != 0) return false;
    }
    return true;
}

size_t Tile::getMemoryFootprint() const noexcept {
    size_t base = sizeof(Tile);
    if (m_isCompressed) {
        return base + m_compressedData.size();
    }
    if (m_buffer) {
        const size_t bufBytes = m_buffer->getSizeInBytes();
        const size_t owners = m_buffer.use_count();
        return base + (owners > 0 ? (bufBytes / owners) : bufBytes);
    }
    return base;
}

} // namespace aladyn::engine::canvas
